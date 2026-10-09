"""ELA module: local JPEG re-save error.

Signal measured: regions whose compression history differs from the rest of
the image light up after a fresh JPEG re-save (error level analysis).
Known failure modes: heavy recompression flattens all differences; inputs
that were never JPEG-compressed (PNG, GIF, BMP) have no error history to
read; tiny or near-flat images give no measurable signal.
Reliability rules: non-JPEG input, min dimension < 96 px, global std < 5,
unmeasurable error (p95 < 1.0), or estimated source quality <= 60 all yield
reliability="unreliable" with status="cannot_determine". Estimated quality
61-85 (or unknown tables) yields "degraded". Thresholds below were tuned on
the dev split only (single q95 save: frac ~0.06; double-history splice:
frac ~0.11): suspicious if high-error fraction > 0.09, confirmed if < 0.075.
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

RESAVE_QUALITY = 90
MIN_DIM = 96
FLAT_STD = 5.0
MIN_P95 = 1.0
Q_UNRELIABLE = 60
Q_DEGRADED = 85
FRAC_SUSPICIOUS = 0.09
FRAC_CONFIRMED = 0.075


class ElaModule(Module):
    """Error-level-analysis check for inconsistent JPEG histories."""

    id = "ela"
    name = "Compression-error check (ELA)"
    media_types = ("image",)

    def applicable(self, media: Media, claim: Claim) -> Applicability:
        _ = claim
        if media.media_type != "image":
            return Applicability(applicable=False, reason="ELA only applies to still images.")
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

        rgb = C.load_rgb(path)
        h, w = rgb.shape[:2]
        if min(h, w) < MIN_DIM:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "The image is too small for this check.",
                f"At {w}x{h}px there are too few pixels to compare regional error levels.",
                Reliability.UNRELIABLE,
                f"Minimum dimension {min(h, w)}px is below the {MIN_DIM}px floor.",
            )
        if float(rgb.std()) < FLAT_STD:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "The image is too uniform for this check.",
                "Near-flat images give almost no re-save error to compare.",
                Reliability.UNRELIABLE,
                "Global pixel std is below the uniformity floor.",
            )
        if not C.is_jpeg(path):
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "This check needs a JPEG file.",
                "Error-level analysis reads JPEG save history, and this file has none.",
                Reliability.UNRELIABLE,
                "Non-JPEG input: no JPEG compression history to compare.",
            )
        quality = C.estimate_jpeg_quality(path)
        reliability = Reliability.OK
        if quality is None:
            reliability = Reliability.DEGRADED
        elif quality <= Q_UNRELIABLE:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "Heavy recompression washed out this signal.",
                f"Quality {quality}: earlier saves were overwritten too aggressively to compare.",
                Reliability.UNRELIABLE,
                f"Estimated JPEG quality {quality} is at or below {Q_UNRELIABLE}.",
            )
        elif quality <= Q_DEGRADED:
            reliability = Reliability.DEGRADED

        resaved = C.jpeg_resave(rgb, RESAVE_QUALITY)
        err = np.abs(rgb - resaved).max(axis=-1)
        p95 = float(np.percentile(err, 95))
        if p95 < MIN_P95:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "No measurable re-save error.",
                "The image barely changed on re-save, leaving nothing to compare between regions.",
                Reliability.UNRELIABLE,
                "95th-percentile error below the measurable floor.",
            )
        med = float(np.median(err))
        mad = float(np.median(np.abs(err - med)))
        frac = float(np.mean(err > med + 3.0 * mad))
        half = w // 2
        asym = float(err[:, half:].mean() / max(err[:, :half].mean(), 1e-6))
        heat = C.save_heatmap(err / p95, "ela")
        artifacts = {"heatmap": heat, "heatmap_peak": C.heatmap_peak(err / p95)}

        if frac > FRAC_SUSPICIOUS:
            return done(
                Status.SUSPICIOUS,
                0.55,
                0.8,
                "One region compresses very differently from the rest.",
                f"{frac:.1%} of pixels show far higher error than typical "
                f"(left/right mean ratio {asym:.1f}), "
                "consistent with parts having different save histories.",
                reliability,
                "Estimated quality above 60."
                if reliability == Reliability.OK
                else "Mid-range quality; a hint.",
                artifacts,
            )
        if frac < FRAC_CONFIRMED and reliability == Reliability.OK:
            return done(
                Status.CONFIRMED,
                0.6,
                0.8,
                "Re-save error looks even across the image.",
                f"Only {frac:.1%} stand out, consistent with one shared save history.",
                reliability,
                "High-quality source with measurable, even error.",
                artifacts,
            )
        return done(
            Status.CANNOT_DETERMINE,
            0.0,
            0.4,
            "Re-save error was inconclusive.",
            f"{frac:.1%} of pixels stand out, between the confirm and concern bands.",
            reliability,
            "Borderline score; absence of evidence is not contradiction.",
            artifacts,
        )


MODULE = ElaModule()
