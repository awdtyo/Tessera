"""Noise module tests, incl. mandated unreliable cases (tiny, q30)."""

from pathlib import Path

import numpy as np
from PIL import Image

from tessera.modules.noise import NoiseModule
from tests.conftest import empty_claim, fixture, load_fixture_rgb, media_for, save_png

MOD = NoiseModule()


def test_unreliable_on_tiny_image(tmp_path: Path) -> None:
    rng = np.random.default_rng(3)
    tiny = save_png(rng.integers(0, 255, (48, 48)).astype(np.uint8), tmp_path / "tiny.png")
    f = MOD.run(media_for(tiny), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"


def test_unreliable_on_heavy_recompression() -> None:
    f = MOD.run(media_for(fixture("dev_recompressed_q30.jpg")), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"


def test_suspicious_on_variance_anomaly(tmp_path: Path) -> None:
    patched = load_fixture_rgb("dev_real.png").copy()
    patched[80:112, 80:112] = patched[80:112, 80:112] * 0.3 + 30
    target = save_png(patched, tmp_path / "patched.png")
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "suspicious"


def test_confirmed_on_uniform_noise() -> None:
    f = MOD.run(media_for(fixture("dev_real.png")), empty_claim())
    assert f.status.value == "confirmed"
    assert f.reliability.value == "ok"


def test_heatmap_matches_original_size() -> None:
    f = MOD.run(media_for(fixture("dev_real.png")), empty_claim())
    with Image.open(f.artifacts["heatmap"]) as heat:
        assert heat.size == (128, 128)
