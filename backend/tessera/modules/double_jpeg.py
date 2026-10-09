"""Double-JPEG module: inconsistent quantization grids.

Signal measured: a second JPEG save imprints its own 8x8 quantization grid.
A region with a different save history shows a different ratio of
misaligned-grid to aligned-grid high-frequency energy. Per 8x8 block, the
DCT is computed with numpy and the log-ratio of shifted vs aligned HF
energy forms the map.
Known failure modes: quality-matched double saves are near-invisible;
crops that shift the 8-grid confuse alignment; heavy single compression
drowns the grid; non-JPEG inputs have no grid at all.
Reliability rules: non-JPEG input is not applicable (no save history).
Min dimension < 64 px, unreadable tables, or estimated quality <= 60 yield
reliability="unreliable" with status="cannot_determine"; unknown tables
yield "degraded". Thresholds tuned on dev only (single q95: median ~0.09;
double-history splice: median ~0.42, tampered half ~1.7 vs clean ~0.06):
suspicious if median > 0.25, confirmed if < 0.15 with reliability ok.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding, Reliability, Status
from tessera.core.media import Media
from tessera.core.module import Module
from tessera.modules import _common as C

logger = logging.getLogger(__name__)

MIN_DIM = 64
Q_UNRELIABLE = 60
MED_SUSPICIOUS = 0.25
MED_CONFIRMED = 0.15

_DCT = np.zeros((8, 8))
for _u in range(8):
    for _x in range(8):
        _DCT[_u, _x] = 0.5 * np.cos(np.pi * (2 * _x + 1) * _u / 16) if _u else 1 / np.sqrt(8)
_DCT[0] *= 1 / np.sqrt(2)

_YY, _XX = np.mgrid[0:8, 0:8]
_HF = (_XX + _YY) >= 6


def _block_energies(gray: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Mean high-frequency abs-DCT energy per 8x8 block, grid offset by dy,dx."""
    h, w = gray.shape
    hh, ww = h // 8 * 8, w // 8 * 8
    shifted = np.roll(gray, (dy, dx), axis=(0, 1))[:hh, :ww]
    shifted = shifted - shifted.mean()
    blocks = shifted.reshape(hh // 8, 8, ww // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 8, 8)
    tmp = np.einsum("uv,nvx->nux", _DCT, blocks)
    coef = np.einsum("nux,xk->nuk", tmp, _DCT.T)
    coef[:, 0, 0] = 0.0
    energies: np.ndarray = np.abs(coef[:, _HF]).mean(axis=1).reshape(hh // 8, ww // 8)
    return energies


def grid_map(gray: np.ndarray) -> np.ndarray:
    """Per-block log-ratio of misaligned vs aligned HF energy."""
    aligned = _block_energies(gray, 0, 0)
    shifted = _block_energies(gray, 4, 4)
    return np.log((shifted + 1e-9) / (aligned + 1e-9))


class DoubleJpegModule(Module):
    """Quantization-grid check for mixed JPEG save histories."""

    id = "double-jpeg"
    name = "Double-save check"
    media_types = ("image",)

    def applicable(self, media: Media, claim: Claim) -> Applicability:
        _ = claim
        if media.media_type != "image":
            return Applicability(applicable=False, reason="Still images only.")
        try:
            if not C.is_jpeg(Path(media.path)):
                return Applicability(applicable=False, reason="Needs JPEG save history.")
        except OSError:
            pass
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

        w, h = C.image_size(path)
        if min(h, w) < MIN_DIM:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "The image is too small for this check.",
                f"At {w}x{h}px there are too few 8x8 blocks to compare grids.",
                Reliability.UNRELIABLE,
                f"Minimum dimension below the {MIN_DIM}px floor.",
            )
        quality = C.estimate_jpeg_quality(path)
        reliability = Reliability.DEGRADED if quality is None else Reliability.OK
        if quality is not None and quality <= Q_UNRELIABLE:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "Heavy compression drowned the grid signal.",
                f"Estimated quality {quality} quantizes away the differences "
                "between single and double saves.",
                Reliability.UNRELIABLE,
                f"Estimated JPEG quality {quality} is at or below {Q_UNRELIABLE}.",
            )

        lr = grid_map(C.load_gray(path))
        score = float(np.median(lr))
        cap = float(np.percentile(lr, 98))
        full = np.kron(np.clip(lr / max(cap, 1e-6), 0, 1), np.ones((8, 8)))
        heat = C.save_heatmap(full, "double-jpeg")
        artifacts = {
            "heatmap": heat,
            "heatmap_peak": C.heatmap_peak(full),
            "quality_estimate": str(quality),
        }

        if score > MED_SUSPICIOUS:
            return done(
                Status.SUSPICIOUS,
                0.5,
                0.75,
                "Save-history hints at two different JPEG pasts.",
                f"Median grid-misfit {score:.2f} is far above a single save, "
                "consistent with regions from different compressions.",
                reliability,
                "Clear grid mismatch."
                if reliability == Reliability.OK
                else "Mismatch on unknown tables; check other tiles.",
                artifacts,
            )
        if score < MED_CONFIRMED and reliability == Reliability.OK:
            return done(
                Status.CONFIRMED,
                0.55,
                0.75,
                "One consistent save grid across the image.",
                f"Median grid-misfit {score:.2f} matches a single JPEG save.",
                reliability,
                "Clean grid on a readable-quality JPEG.",
                artifacts,
            )
        return done(
            Status.CANNOT_DETERMINE,
            0.0,
            0.4,
            "Save-history comparison was inconclusive.",
            f"Median grid-misfit {score:.2f} sits between the bands.",
            reliability,
            "Borderline score; absence of evidence is not contradiction.",
            artifacts,
        )


MODULE = DoubleJpegModule()
