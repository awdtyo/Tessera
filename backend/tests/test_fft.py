"""FFT module tests, incl. mandated unreliable case (tiny image)."""

from pathlib import Path

import numpy as np

from tessera.modules.fft import FftModule
from tests.conftest import empty_claim, fixture, media_for, save_png

MOD = FftModule()


def test_unreliable_on_tiny_image(tmp_path: Path) -> None:
    rng = np.random.default_rng(5)
    tiny = save_png(rng.integers(0, 255, (64, 64)).astype(np.uint8), tmp_path / "tiny.png")
    f = MOD.run(media_for(tiny), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"


def test_suspicious_on_periodic_grid(tmp_path: Path) -> None:
    yy, xx = np.mgrid[0:128, 0:128]
    grid = 128 + 100 * np.sin(2 * np.pi * xx / 8) * np.sin(2 * np.pi * yy / 8)
    target = save_png(grid, tmp_path / "grid.png")
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "suspicious"


def test_confirmed_on_clean_fullsize_spectrum(tmp_path: Path) -> None:
    rng = np.random.default_rng(11)
    xs = np.linspace(0, 255, 256)
    ys = np.linspace(0, 255, 256)
    gx, gy = np.meshgrid(xs, ys)
    clean = 0.5 * gx + 0.5 * gy + rng.integers(0, 30, size=(256, 256))
    target = save_png(clean, tmp_path / "clean256.png")
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "confirmed"
    assert f.reliability.value == "ok"


def test_cannot_determine_on_small_degraded_input() -> None:
    """128px dev fixture: honest cannot_determine, never a forced verdict."""
    f = MOD.run(media_for(fixture("dev_real.png")), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "degraded"


def test_spectrum_artifact_exists(tmp_path: Path) -> None:
    rng = np.random.default_rng(11)
    target = save_png(rng.integers(0, 255, (256, 256)).astype(np.uint8), tmp_path / "n256.png")
    f = MOD.run(media_for(target), empty_claim())
    assert Path(f.artifacts["spectrum"]).is_file()
    assert "spectrum_peak" in f.artifacts
