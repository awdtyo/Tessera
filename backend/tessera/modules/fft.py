"""FFT-spectrum module: periodic resampling / synthesis fingerprints.

Signal measured: resampling (rotation, scaling, splicing with interpolation)
and some generators leave sharp peaks in the Fourier magnitude spectrum that
natural photos lack. Score = max-to-median ratio in a high-frequency ring
(outside 15% and inside 45% of the half-size), DC excluded.
Known failure modes: recompression erases high frequencies; small images
give too coarse a spectrum; natural repeating textures (fabrics, screens)
cause false peaks.
Reliability rules: min dimension < 128 px or estimated JPEG quality <= 60
yields reliability="unreliable" with status="cannot_determine". Quality
61-85 or min dimension < 256 yields "degraded". Thresholds tuned on dev
only (natural/synthetic: ratio ~1.2-1.6; periodic grid: ratio ~40000):
suspicious if ratio > 3.0, confirmed if < 2.0 with reliability ok.
Artifact note: the spectrum lives in frequency space, so it is stored as
artifacts["spectrum"] (not "heatmap") with the peak in spectrum pixels.
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

MIN_DIM = 128
DEGRADED_DIM = 256
Q_UNRELIABLE = 60
Q_DEGRADED = 85
RATIO_SUSPICIOUS = 3.0
RATIO_CONFIRMED = 2.0


def spectrum(gray: np.ndarray) -> np.ndarray:
    """Log-magnitude FFT spectrum with Hann windowing."""
    h, w = gray.shape
    window = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    centered = (gray - gray.mean()) * window
    spec = np.fft.fftshift(np.fft.fft2(centered))
    return np.log1p(np.abs(spec))


def peak_ratio(mag: np.ndarray) -> tuple[float, tuple[int, int]]:
    """Max-to-median ratio in the high-frequency ring; plus peak coords."""
    h, w = mag.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - h / 2.0) ** 2 + (xx - w / 2.0) ** 2)
    ring = (r > 0.15 * min(h, w)) & (r < 0.45 * min(h, w))
    band = mag[ring]
    med = float(np.median(band))
    idx = int(np.argmax(np.where(ring, mag, -np.inf)))
    py, px = divmod(idx, w)
    return float(band.max() / (med + 1e-9)), (px, py)


class FftModule(Module):
    """Frequency-spectrum check for periodic manipulation traces."""

    id = "fft"
    name = "Frequency-spectrum check"
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

        w, h = C.image_size(path)
        if min(h, w) < MIN_DIM:
            return done(
                Status.CANNOT_DETERMINE,
                0.0,
                0.3,
                "The image is too small for this check.",
                f"At {w}x{h}px the spectrum is too coarse to read periodic traces.",
                Reliability.UNRELIABLE,
                f"Minimum dimension below the {MIN_DIM}px floor.",
            )
        reliability = Reliability.OK
        if min(h, w) < DEGRADED_DIM:
            reliability = Reliability.DEGRADED
        if C.is_jpeg(path):
            quality = C.estimate_jpeg_quality(path)
            if quality is not None and quality <= Q_UNRELIABLE:
                return done(
                    Status.CANNOT_DETERMINE,
                    0.0,
                    0.3,
                    "Heavy recompression erased this signal.",
                    f"Quality {quality} suppresses the high frequencies this check reads.",
                    Reliability.UNRELIABLE,
                    f"Estimated JPEG quality {quality} is at or below {Q_UNRELIABLE}.",
                )
            if quality is None or quality <= Q_DEGRADED:
                reliability = Reliability.DEGRADED

        mag = spectrum(C.load_gray(path))
        ratio, (px, py) = peak_ratio(mag)
        spec_path = C.save_heatmap(mag / (mag.max() + 1e-9), "fft-spectrum")
        artifacts = {"spectrum": spec_path, "spectrum_peak": f"{px},{py},{ratio:.2f}"}

        if ratio > RATIO_SUSPICIOUS:
            return done(
                Status.SUSPICIOUS,
                0.5,
                0.75,
                "The spectrum shows sharp periodic traces.",
                f"A frequency peak {ratio:.1f}x above typical is consistent "
                "with resampling or synthesis fingerprints.",
                reliability,
                "Strong peak."
                if reliability == Reliability.OK
                else "Strong peak, weakened signal; check other tiles.",
                artifacts,
            )
        if ratio < RATIO_CONFIRMED and reliability == Reliability.OK:
            return done(
                Status.CONFIRMED,
                0.55,
                0.75,
                "The spectrum shows no periodic traces.",
                f"Peak ratio {ratio:.2f} is ordinary; no resampling fingerprints stand out.",
                reliability,
                "Clean spectrum on a full-size, full-quality input.",
                artifacts,
            )
        return done(
            Status.CANNOT_DETERMINE,
            0.0,
            0.4,
            "The spectrum was inconclusive.",
            f"Peak ratio {ratio:.2f} sits between the confirm and concern bands, "
            "or the signal is weakened.",
            reliability,
            "Borderline or weakened signal; absence of evidence is not contradiction.",
            artifacts,
        )


MODULE = FftModule()
