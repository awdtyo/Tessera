"""Copy-move module: duplicated regions within one image.

Signal measured: classical block matching. Overlapping 16x16 blocks
(stride 8) are normalized, sorted lexicographically by a 16-dim signature,
and near-identical pairs far apart vote for their shift; shifts with enough
votes mark cloned regions.
Known failure modes: flat areas self-match (false positives); scaled or
rotated clones are missed; tiny images leave no room for offsets; heavy
JPEG blocks confuse matching.
Reliability rules: min dimension < 96 px or > 50% flat area yields
reliability="unreliable" with status="cannot_determine". Estimated JPEG
quality <= 70 yields "degraded". Thresholds tuned on dev only (clean: no
shift above 0 votes; 24x24 clone in 128px: shift (64,64) with 4 votes):
suspicious if best shift has >= 4 votes covering >= 0.3% of pixels.
Performance: inputs are downscaled to max-dim 512 first, keeping runtime
far under the ~10 s budget (fixtures: < 0.1 s).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image

from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding, Reliability, Status
from tessera.core.media import Media
from tessera.core.module import Module
from tessera.modules import _common as C

logger = logging.getLogger(__name__)

MIN_DIM = 96
Q_DEGRADED = 70
FLAT_FRAC = 0.50
MAX_DIM = 512
BLOCK = 16
STRIDE = 8
MIN_OFFSET = 32
VOTES_SUSPICIOUS = 4
AREA_FRAC = 0.003


def _match(gray: np.ndarray) -> tuple[tuple[int, int] | None, int, np.ndarray]:
    """Return (best shift, votes, boolean mask) for cloned blocks."""
    h, w = gray.shape
    ys = list(range(0, h - BLOCK + 1, STRIDE))
    xs = list(range(0, w - BLOCK + 1, STRIDE))
    spots = [(y, x) for y in ys for x in xs]
    feats = np.stack([gray[y : y + BLOCK, x : x + BLOCK].ravel() for y, x in spots])
    feats = feats.astype(float)
    feats = (feats - feats.mean(axis=1, keepdims=True)) / (feats.std(axis=1, keepdims=True) + 1e-9)
    order = np.lexsort(feats[:, ::16].T[::-1])
    votes: dict[tuple[int, int], int] = {}
    pairs: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for i in range(len(order) - 1):
        a, b = int(order[i]), int(order[i + 1])
        if float(np.linalg.norm(feats[a] - feats[b])) > 2.0:
            continue
        (ya, xa), (yb, xb) = spots[a], spots[b]
        if abs(ya - yb) + abs(xa - xb) < MIN_OFFSET:
            continue
        shift = (yb - ya, xb - xa)
        votes[shift] = votes.get(shift, 0) + 1
        pairs.setdefault(shift, []).extend([(ya, xa), (yb, xb)])
    if not votes:
        return None, 0, np.zeros((h, w), dtype=bool)
    best = max(votes, key=lambda s: votes[s])
    mask = np.zeros((h, w), dtype=bool)
    for y, x in pairs[best]:
        mask[y : y + BLOCK, x : x + BLOCK] = True
    return best, votes[best], mask


class CopyMoveModule(Module):
    """Block-matching check for cloned regions."""

    id = "copy-move"
    name = "Copy-move check"
    media_types = ("image",)

    def applicable(self, media: Media, claim: Claim) -> Applicability:
        _ = claim
        if media.media_type != "image":
            return Applicability(applicable=False, reason="Still images only.")
        return Applicability(applicable=True, reason="Image input.")

    def run(self, media: Media, claim: Claim) -> Finding:
        _ = claim
        start = time.perf_counter()
        path = Path(media.path)

        def done(
            status: Status,
            lo: float,
            hi: float,
            summary: str,
            reasoning: str,
            reliability: Reliability,
            note: str,
            artifacts: dict[str, str] | None = None,
        ) -> Finding:
            return Finding(
                module_id=self.id,
                status=status,
                confidence_low=lo,
                confidence_high=hi,
                summary=summary,
                reasoning=reasoning,
                reliability=reliability,
                reliability_note=note,
                artifacts=artifacts or {},
                runtime_ms=int((time.perf_counter() - start) * 1000),
            )

        gray = C.load_gray(path)
        h, w = gray.shape
        if min(h, w) < MIN_DIM:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "The image is too small for this check.",
                f"At {w}x{h}px there is no room for meaningful offsets.",
                Reliability.UNRELIABLE,
                f"Minimum dimension below the {MIN_DIM}px floor.",
            )
        flat_frac = float(np.mean(np.abs(gray - C.median3(gray)) < 2.0))
        if flat_frac > FLAT_FRAC:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "Too much flat area: everything matches everything.",
                f"{flat_frac:.0%} near-uniform, so matching cannot discriminate.",
                Reliability.UNRELIABLE,
                "Flat-area fraction above the usable ceiling.",
            )
        reliability = Reliability.OK
        if C.is_jpeg(path):
            quality = C.estimate_jpeg_quality(path)
            if quality is not None and quality <= Q_DEGRADED:
                reliability = Reliability.DEGRADED

        scale = min(1.0, MAX_DIM / max(h, w))
        if scale < 1.0:
            small = np.asarray(
                Image.fromarray(gray.astype(np.uint8)).resize(
                    (int(w * scale), int(h * scale)), Image.BILINEAR
                ),
                dtype=float,
            )
        else:
            small = gray
        shift, nvotes, mask_small = _match(small)
        if scale < 1.0:
            mask_img = Image.fromarray(mask_small).resize((w, h), Image.NEAREST)
            mask = np.asarray(mask_img, dtype=bool)
        else:
            mask = mask_small
        area_frac = float(mask.mean())
        heat = C.save_heatmap(mask.astype(float), "copy-move")
        artifacts = {"heatmap": heat, "heatmap_peak": C.heatmap_peak(mask.astype(float))}
        shift_txt = f"shift {shift} with {nvotes} votes" if shift else "no candidate shift"

        if shift is not None and nvotes >= VOTES_SUSPICIOUS and area_frac >= AREA_FRAC:
            return done(
                Status.SUSPICIOUS,
                0.5,
                0.8,
                "A copied region was found inside the image.",
                f"Blocks repeat at {shift_txt}, covering {area_frac:.1%} "
                "of the image: consistent with copy-move editing.",
                reliability,
                "Repeated blocks with a coherent offset."
                if reliability == Reliability.OK
                else "Repeat found, but compression weakens matching.",
                artifacts,
            )
        if (shift is None or nvotes <= 2) and reliability == Reliability.OK:
            return done(
                Status.CONFIRMED,
                0.5,
                0.7,
                "No repeated regions found.",
                f"Block matching surfaced {shift_txt}; nothing clone-like.",
                reliability,
                "Clean match table on a full-quality input.",
                artifacts,
            )
        return done(
            Status.CANNOT_DETERMINE,
            0.0,
            0.4,
            "Clone search was inconclusive.",
            f"{shift_txt}; below the concern band but above a clean bill.",
            reliability,
            "Borderline score; absence of evidence is not contradiction.",
            artifacts,
        )


MODULE = CopyMoveModule()
