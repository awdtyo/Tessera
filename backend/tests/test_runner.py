"""(2) A crashing module is isolated into cannot_determine / error."""

from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding
from tessera.core.media import Media
from tessera.core.module import Module
from tessera.core.runner import run_all


class CrashingModule(Module):
    id = "crashing"
    name = "Crashing check"
    media_types = ("image", "video")

    def applicable(self, media: Media, claim: Claim) -> Applicability:
        _ = (media, claim)
        return Applicability(applicable=True, reason="Always applies; then crashes.")

    def run(self, media: Media, claim: Claim) -> Finding:
        _ = (media, claim)
        raise RuntimeError("boom")


def test_crashing_module_becomes_error_finding() -> None:
    media = Media(path="fixture.jpg", media_type="image")
    findings = run_all(media, modules=[CrashingModule()])
    assert len(findings) == 1
    f = findings[0]
    assert f.module_id == "crashing"
    assert f.status.value == "cannot_determine"
    assert f.reliability.value == "error"


def test_crash_does_not_take_down_siblings() -> None:
    from tessera.modules.dummy import DummyModule

    media = Media(path="fixture.jpg", media_type="image")
    findings = run_all(media, modules=[CrashingModule(), DummyModule()])
    by_id = {f.module_id: f for f in findings}
    assert by_id["crashing"].reliability.value == "error"
    assert by_id["dummy"].status.value == "confirmed"
