"""Metadata+C2PA tests, incl. mandated unreliable case (stripped metadata)."""

from pathlib import Path

import numpy as np
from PIL import Image

from tessera.modules.metadata_c2pa import MetadataC2paModule
from tests.conftest import empty_claim, fixture, load_fixture_rgb, media_for

MOD = MetadataC2paModule()


def _jpeg_with_exif(dest: Path, tags: dict[int, str]) -> Path:
    arr = load_fixture_rgb("dev_real.png")
    exif = Image.Exif()
    for tag, value in tags.items():
        exif[tag] = value
    Image.fromarray(arr.astype(np.uint8)).save(dest, format="JPEG", quality=95, exif=exif)
    return dest


def test_unreliable_without_metadata() -> None:
    """Stripped metadata (the social-media norm) is ignorance, not evidence."""
    f = MOD.run(media_for(fixture("dev_real.png")), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "unreliable"
    assert f.artifacts["c2pa"].startswith("absent")


def test_suspicious_on_editor_tag(tmp_path: Path) -> None:
    target = _jpeg_with_exif(tmp_path / "edited.jpg", {271: "TestCam", 305: "Adobe Photoshop"})
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "suspicious"
    assert f.artifacts["software"] == "Adobe Photoshop"


def test_confirmed_on_clean_camera_exif(tmp_path: Path) -> None:
    target = _jpeg_with_exif(tmp_path / "clean.jpg", {271: "TestCam", 272: "T-100"})
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "confirmed"
    assert f.reliability.value == "ok"


def test_cannot_determine_on_unknown_software(tmp_path: Path) -> None:
    target = _jpeg_with_exif(tmp_path / "odd.jpg", {271: "TestCam", 305: "SomeFirmware 2.1"})
    f = MOD.run(media_for(target), empty_claim())
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "degraded"


def test_not_applicable_to_video() -> None:
    decision = MOD.applicable(media_for(fixture("dev_real.png"), "video"), empty_claim())
    assert decision.applicable is False
