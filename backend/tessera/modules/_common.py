"""Shared private helpers for classical image modules. Not a module itself.

Provides: JPEG detection, JPEG quality estimation from quantization tables,
grayscale/RGB loading, and full-resolution grayscale heatmap writing.
Only Pillow + numpy. Deterministic; no network; no global state.
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)

JPEG_MAGIC = b"\xff\xd8"

# IJG Annex K luminance base table (K.1), row-major order, for quality matching.
_LUM_BASE = np.array(
    [
        16,
        11,
        10,
        16,
        24,
        40,
        51,
        61,
        12,
        12,
        14,
        19,
        26,
        58,
        60,
        55,
        14,
        13,
        16,
        24,
        40,
        57,
        69,
        56,
        14,
        17,
        22,
        29,
        51,
        87,
        80,
        62,
        18,
        22,
        37,
        56,
        68,
        109,
        103,
        77,
        24,
        35,
        55,
        64,
        81,
        104,
        113,
        92,
        49,
        64,
        78,
        87,
        103,
        121,
        120,
        101,
        72,
        92,
        95,
        98,
        112,
        100,
        103,
        99,
    ],
    dtype=np.float64,
)

# Zigzag index: position i in zigzag order sits at natural index _ZIGZAG[i].
_ZIGZAG = np.array(
    [
        0,
        1,
        8,
        16,
        9,
        2,
        3,
        10,
        17,
        24,
        32,
        25,
        18,
        11,
        4,
        5,
        12,
        19,
        26,
        33,
        40,
        48,
        41,
        34,
        27,
        20,
        13,
        6,
        7,
        14,
        21,
        28,
        35,
        42,
        49,
        56,
        57,
        50,
        43,
        36,
        29,
        22,
        15,
        23,
        30,
        37,
        44,
        51,
        58,
        59,
        52,
        45,
        38,
        31,
        39,
        46,
        53,
        60,
        61,
        54,
        47,
        55,
        62,
        63,
    ]
)

_QUALITY_TOLERANCE = 0.20  # mean relative error allowed for a table match


def is_jpeg(path: Path) -> bool:
    """True when file starts with the JPEG SOI marker (magic bytes, not suffix)."""
    try:
        with open(path, "rb") as fh:
            return fh.read(2) == JPEG_MAGIC
    except OSError:
        return False


def _scaled_base(quality: int) -> np.ndarray:
    if quality < 50:
        scale = 5000.0 / quality
    else:
        scale = 200.0 - 2.0 * quality
    return np.clip(np.floor((_LUM_BASE * scale + 50.0) / 100.0), 1, 255)


def estimate_jpeg_quality(path: Path) -> int | None:
    """Estimate JPEG save quality via quantization-table matching.

    Compares the luminance table against IJG-scaled references for Q=10..95,
    trying both natural and zigzag coefficient orders (Pillow's order is not
    relied upon). Returns None for non-JPEGs, missing tables, or no match.
    """
    if not is_jpeg(path):
        return None
    try:
        with Image.open(path) as img:
            tables = img.quantization
    except Exception as exc:  # noqa: BLE001 - unreadable file, not fatal here
        logger.debug("Could not read quantization tables from %s: %s", path, exc)
        return None
    if not tables or 0 not in tables:
        return None
    observed = np.array(tables[0], dtype=np.float64)
    if observed.shape != (64,):
        return None
    candidates = [observed, observed[np.argsort(_ZIGZAG)]]
    best_q: int | None = None
    best_err = _QUALITY_TOLERANCE
    for q in range(10, 96):
        ref = _scaled_base(q)
        for cand in candidates:
            err = float(np.mean(np.abs(cand - ref) / ref))
            if err < best_err:
                best_err = err
                best_q = q
    return best_q


def load_rgb(path: Path) -> np.ndarray:
    """Load image as float64 RGB array."""
    with Image.open(path) as img:
        return np.asarray(img.convert("RGB"), dtype=np.float64)


def load_gray(path: Path) -> np.ndarray:
    """Load image as float64 grayscale array."""
    with Image.open(path) as img:
        return np.asarray(img.convert("L"), dtype=np.float64)


def image_size(path: Path) -> tuple[int, int]:
    """Return (width, height) without fully decoding."""
    with Image.open(path) as img:
        size: tuple[int, int] = (int(img.size[0]), int(img.size[1]))
        return size


def median3(gray: np.ndarray) -> np.ndarray:
    """3x3 median filter (Pillow, deterministic)."""
    img = Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8), mode="L")
    return np.asarray(img.filter(ImageFilter.MedianFilter(3)), dtype=np.float64)


def save_heatmap(normalized: np.ndarray, stem: str) -> str:
    """Write a 0..1 float map as a full-resolution grayscale PNG; return abs path.

    Grayscale keeps the mapping unambiguous (bright = stronger signal).
    Files go to a fresh tempdir; the caller records the path in artifacts.
    """
    clipped = np.clip(normalized, 0.0, 1.0)
    out = Path(tempfile.mkdtemp(prefix=f"tessera-{stem}-")) / f"{stem}_heatmap.png"
    Image.fromarray((clipped * 255).astype(np.uint8), mode="L").save(out, format="PNG")
    logger.debug("Wrote heatmap %s", out)
    return str(out)


def heatmap_peak(normalized: np.ndarray) -> str:
    """Peak location and value as 'x,y,value' in original pixel coordinates."""
    idx = int(np.argmax(normalized))
    y, x = divmod(idx, normalized.shape[1])
    return f"{x},{y},{float(normalized[y, x]):.3f}"


def jpeg_resave(arr: np.ndarray, quality: int) -> np.ndarray:
    """Round-trip a float RGB array through JPEG at the given quality."""
    buf = io.BytesIO()
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB").save(
        buf, format="JPEG", quality=quality
    )
    buf.seek(0)
    with Image.open(buf) as img:
        return np.asarray(img.convert("RGB"), dtype=np.float64)
