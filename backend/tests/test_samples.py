"""Sample-set tests. All offline; never touch the network or heldout for tuning."""

import hashlib
from pathlib import Path

from PIL import Image

from tessera.samples.loader import (
    by_category,
    default_manifest_path,
    dev_entries,
    heldout_entries,
    load_manifest,
    missing_files,
    resolve,
)


def test_manifest_loads_and_files_exist() -> None:
    entries = load_manifest()
    assert len(entries) >= 8
    assert missing_files(entries) == []


def test_default_path_points_at_repo_manifest() -> None:
    assert (
        default_manifest_path() == Path(__file__).resolve().parents[2] / "samples" / "manifest.json"
    )


def test_splits_cover_dev_and_heldout() -> None:
    entries = load_manifest()
    assert len(dev_entries(entries)) >= 6
    assert len(heldout_entries(entries)) >= 2


def test_dev_helpers_exclude_heldout() -> None:
    """Split discipline: dev views must never include heldout files."""
    entries = load_manifest()
    dev_files = {e.file for e in dev_entries(entries)}
    heldout_files = {e.file for e in heldout_entries(entries)}
    assert dev_files.isdisjoint(heldout_files)


def test_required_fields_present() -> None:
    for e in load_manifest():
        assert e.file and e.source.strip() and e.license.strip()
        assert "manipulated" in e.ground_truth


def test_splice_differs_from_real() -> None:
    entries = load_manifest()
    real = resolve(by_category(dev_entries(entries), "real")[0])
    splice = resolve(by_category(dev_entries(entries), "splice")[0])
    assert real.read_bytes() != splice.read_bytes()


def test_recompressed_is_small_jpeg() -> None:
    entries = load_manifest()
    wa = resolve(by_category(dev_entries(entries), "whatsapp-recompressed")[0])
    raw = wa.read_bytes()
    assert raw[:2] == b"\xff\xd8"  # JPEG magic
    real = resolve(by_category(dev_entries(entries), "real")[0])
    assert len(raw) < real.stat().st_size


def test_copymove_ground_truth_has_regions() -> None:
    entries = load_manifest()
    cm = by_category(dev_entries(entries), "copy-move")[0]
    assert cm.ground_truth["type"] == "copy-move"
    assert "copied_region" in cm.ground_truth and "pasted_at" in cm.ground_truth


def test_video_fixtures_are_multiframe() -> None:
    entries = load_manifest()
    for cat in ("video-real", "video-spliced"):
        path = resolve(by_category(dev_entries(entries), cat)[0])  # type: ignore[arg-type]
        with Image.open(path) as img:
            assert getattr(img, "n_frames", 1) == 8


def test_manifest_hashes_match_files() -> None:
    for e in load_manifest():
        if e.sha256 is None:
            continue
        assert hashlib.sha256(resolve(e).read_bytes()).hexdigest() == e.sha256
