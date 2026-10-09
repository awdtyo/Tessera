"""ELA module tests, incl. mandated unreliable cases (PNG, q30)."""

from pathlib import Path

import numpy as np
from PIL import Image

from tessera.modules.ela import ElaModule
from tests.conftest import empty_claim, fixture, load_fixture_rgb, media_for, save_jpeg

MOD = ElaModule()


def _double_history_splice(dest: Path) -> Path:
    real = load_fixture_rgb("dev_real.png")
    other = load_fixture_rgb("dev_splice.png")
    w = real.shape[1]
    tmp_a = dest.parent / "half_a_q70.jpg"
    tmp_b = dest.parent / "half_b_q95.jpg"
    save_jpeg(real, tmp_a, 70)
    save_jpeg(other, tmp_b, 95)
    with Image.open(tmp_a) as ia, Image.open(tmp_b) as ib:
        a = np.asarray(ia.convert("RGB"), dtype=np.float64)
        b = np.asarray(ib.convert("RGB"), dtype=np.float64)
    combined = np.concatenate([a[:, : w // 2], b[:, w // 2 :]], axis=1)
    return save_jpeg(combined, dest, 95)


def test_unreliable_on_png_without_jpeg_history() -> None:
    f = MOD.run(media_for(fixture("dev_real.png")), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"


def test_unreliable_on_heavy_recompression() -> None:
    f = MOD.run(media_for(fixture("dev_recompressed_q30.jpg")), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"


def test_suspicious_on_double_history_splice(tmp_path: Path) -> None:
    target = _double_history_splice(tmp_path / "dbl.jpg")
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "suspicious"
    assert f.reliability.value in ("ok", "degraded")
    assert Path(f.artifacts["heatmap"]).is_file()


def test_confirmed_on_single_save(tmp_path: Path) -> None:
    target = save_jpeg(load_fixture_rgb("dev_real.png"), tmp_path / "single.jpg", 95)
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "confirmed"


def test_heatmap_matches_original_size(tmp_path: Path) -> None:
    target = save_jpeg(load_fixture_rgb("dev_real.png"), tmp_path / "single.jpg", 95)
    f = MOD.run(media_for(target), empty_claim())
    with Image.open(f.artifacts["heatmap"]) as heat:
        assert heat.size == (128, 128)
    assert "heatmap_peak" in f.artifacts


def test_not_applicable_to_video() -> None:
    decision = MOD.applicable(media_for(fixture("dev_real.png"), "video"), empty_claim())
    assert decision.applicable is False
