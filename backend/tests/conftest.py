"""Shared fixtures for module tests: sample paths, media makers, JPEG builders."""

from pathlib import Path

import numpy as np
from PIL import Image

from tessera.core.claim import Claim
from tessera.core.media import Media

SAMPLES = Path(__file__).resolve().parents[2] / "samples" / "fixtures"


def fixture(name: str) -> Path:
    """Path to a generated sample fixture (dev split unless stated)."""
    return SAMPLES / name


def media_for(path: Path, media_type: str = "image") -> Media:
    """Build a Media record for a local file."""
    return Media(path=str(path), media_type=media_type)  # type: ignore[arg-type]


def empty_claim() -> Claim:
    """Modules in this phase ignore claims; tests pass an empty one."""
    return Claim()


def save_jpeg(arr: np.ndarray, dest: Path, quality: int) -> Path:
    """Deterministically save an RGB array as JPEG (for history tests)."""
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB").save(
        dest, format="JPEG", quality=quality
    )
    return dest


def save_png(arr: np.ndarray, dest: Path) -> Path:
    """Deterministically save an RGB or L array as PNG."""
    mode = "L" if arr.ndim == 2 else "RGB"
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode=mode).save(dest, format="PNG")
    return dest


def load_fixture_rgb(name: str) -> np.ndarray:
    """Load a sample fixture as a float RGB array."""
    with Image.open(fixture(name)) as img:
        return np.asarray(img.convert("RGB"), dtype=np.float64)
