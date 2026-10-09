"""Noise-residual module: local sensor-noise variance.

Signal measured: the fine noise left by a camera sensor (or a generator)
should be roughly uniform; a pasted, smoothed, or regenerated patch usually
has clearly lower or higher local variance. Residual = gray - 3x3 median,
local variance via box means; score = fraction of pixels whose local
variance deviates far from the median.
Known failure modes: denoised or heavily recompressed inputs; naturally
flat areas (sky, walls) that carry no noise to compare; uniform high-ISO
grain that hides patches.
Reliability rules: min dimension < 96 px, estimated JPEG quality <= 60, or
> 40% near-flat pixels yield reliability="unreliable" with
status="cannot_determine". Quality 61-85 yields "degraded". Thresholds tuned
on dev only (clean: frac ~0.035-0.046; variance anomaly: frac ~0.078):
suspicious if frac > 0.065, confirmed if < 0.055.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding, Reliability, Status
from tessera.core.media import Media
from tessera.core.module import Module
from tessera.modules import _common as C

logger = logging.getLogger(__name__)

MIN_DIM = 96
Q_UNRELIABLE = 60
Q_DEGRADED = 85
FLAT_FRAC = 0.40
FRAC_SUSPICIOUS = 0.065
FRAC_CONFIRMED = 0.055


def _boxmean(a: np.ndarray, radius: int) -> np.ndarray:
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), mode="L")
    return np.asarray(img.filter(ImageFilter.BoxBlur(radius)), dtype=np.float64)


class NoiseModule(Module):
    """Local-variance check for inconsistent noise patterns."""

    id = "noise"
    name = "Noise-pattern check"
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
                f"At {w}x{h}px local variance cannot be estimated reliably.",
                Reliability.UNRELIABLE,
                f"Minimum dimension below the {MIN_DIM}px floor.",
            )
        flat_frac = float(np.mean(np.abs(gray - C.median3(gray)) < 2.0))
        if flat_frac > FLAT_FRAC:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "Too much flat area to compare noise.",
                f"{flat_frac:.0%} near-uniform: too little texture to compare.",
                Reliability.UNRELIABLE,
                "Flat-area fraction above the usable ceiling.",
            )
        reliability = Reliability.OK
        if C.is_jpeg(path):
            quality = C.estimate_jpeg_quality(path)
            if quality is not None and quality <= Q_UNRELIABLE:
                return done(
                    Status.CANNOT_DETERMINE,
                    0.0,
                    0.3,
                    "Heavy recompression washed out this signal.",
                    f"Estimated source quality {quality} overwrites the original noise pattern.",
                    Reliability.UNRELIABLE,
                    f"Estimated JPEG quality {quality} is at or below {Q_UNRELIABLE}.",
                )
            if quality is None or quality <= Q_DEGRADED:
                reliability = Reliability.DEGRADED

        residual = gray - C.median3(gray)
        local_var = np.clip(_boxmean(residual**2, 2) - _boxmean(residual, 2) ** 2, 0, None)
        med = float(np.median(local_var))
        mad = float(np.median(np.abs(local_var - med)))
        dev = np.abs(local_var - med) / (3.0 * mad + 1e-6)
        frac = float(np.mean(dev > 1.0))
        heat = C.save_heatmap(np.clip(dev / 3.0, 0, 1), "noise")
        artifacts = {"heatmap": heat, "heatmap_peak": C.heatmap_peak(dev)}

        if frac > FRAC_SUSPICIOUS:
            return done(
                Status.SUSPICIOUS,
                0.5,
                0.75,
                "One area's noise stands out from the rest.",
                f"{frac:.1%} of pixels deviate far from the typical noise level, "
                "consistent with a pasted or smoothed patch.",
                reliability,
                "Clear variance anomaly."
                if reliability == Reliability.OK
                else "Anomaly despite mid-range quality.",
                artifacts,
            )
        if frac < FRAC_CONFIRMED and reliability == Reliability.OK:
            return done(
                Status.CONFIRMED,
                0.55,
                0.75,
                "Camera noise looks even across the image.",
                f"Only {frac:.1%} of pixels deviate, consistent with one uniform source.",
                reliability,
                "Even noise on a full-quality input.",
                artifacts,
            )
        return done(
            Status.CANNOT_DETERMINE,
            0.0,
            0.4,
            "Noise comparison was inconclusive.",
            f"{frac:.1%} of pixels deviate, between the confirm and concern bands.",
            reliability,
            "Borderline score; absence of evidence is not contradiction.",
            artifacts,
        )


MODULE = NoiseModule()
