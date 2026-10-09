"""Dummy module (Phase 0 placeholder).

Signal measured: none — proves plug-in discovery and the runner path.
Known failure modes: none; always applicable in Phase 0.
Reliability rules: always ``ok``; real modules must return
``unreliable``/``cannot_determine`` when their signal is weak.
"""

from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding, Reliability, Status
from tessera.core.media import Media
from tessera.core.module import Module


class DummyModule(Module):
    """Trivial always-applicable check used by scaffold tests."""

    id = "dummy"
    name = "Dummy check"
    media_types = ("image", "video")

    def applicable(self, media: Media, claim: Claim) -> Applicability:
        _ = (media, claim)
        return Applicability(applicable=True, reason="Dummy applies to all media in Phase 0.")

    def run(self, media: Media, claim: Claim) -> Finding:
        _ = (media, claim)
        return Finding(
            module_id=self.id,
            status=Status.CONFIRMED,
            confidence_low=0.9,
            confidence_high=1.0,
            summary="The scaffold check ran successfully.",
            reasoning="This is a placeholder that confirms the runner executed it.",
            reliability=Reliability.OK,
            reliability_note="Placeholder signal; always trustworthy as a wiring check.",
            artifacts={},
            runtime_ms=0,
        )


MODULE = DummyModule()
