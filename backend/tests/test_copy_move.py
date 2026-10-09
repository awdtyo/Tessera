"""Copy-move tests, incl. mandated unreliable cases (tiny, flat)."""

from pathlib import Path

import numpy as np
from PIL import Image

from tessera.modules.copy_move import CopyMoveModule
from tests.conftest import empty_claim, fixture, media_for, save_png

MOD = CopyMoveModule()


def test_unreliable_on_tiny_image(tmp_path: Path) -> None:
    rng = np.random.default_rng(21)
    tiny = save_png(rng.integers(0, 255, (48, 48)).astype(np.uint8), tmp_path / "tiny.png")
    f = MOD.run(media_for(tiny), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"


def test_unreliable_on_flat_image(tmp_path: Path) -> None:
    flat = save_png(np.full((128, 128, 3), 200, dtype=np.uint8), tmp_path / "flat.png")
    f = MOD.run(media_for(flat), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"


def test_suspicious_on_clone_fixture() -> None:
    f = MOD.run(media_for(fixture("dev_copymove.png")), empty_claim())
    assert f.status.value == "suspicious"
    assert f.reliability.value == "ok"
    with Image.open(f.artifacts["heatmap"]) as heat:
        mask = np.asarray(heat.convert("L")) > 0
        assert heat.size == (128, 128)
        assert mask[80:104, 80:104].any()  # pasted region is marked


def test_confirmed_on_clean_image() -> None:
    f = MOD.run(media_for(fixture("dev_real.png")), empty_claim())
    assert f.status.value == "confirmed"
