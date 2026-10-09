"""(1) Runner auto-discovers the dummy plug-in module."""

from tessera.core.media import Media
from tessera.core.registry import discover_modules
from tessera.core.runner import run_all


def test_dummy_is_discovered() -> None:
    ids = [m.id for m in discover_modules()]
    assert "dummy" in ids


def test_run_all_executes_dummy() -> None:
    media = Media(path="fixture.jpg", media_type="image")
    findings = run_all(media)
    by_id = {f.module_id: f for f in findings}
    assert "dummy" in by_id
    assert by_id["dummy"].status.value == "confirmed"
