"""Runner: executes applicable modules, isolates crashes.

A crashing module never crashes a run: the exception becomes a
``cannot_determine`` Finding with ``reliability="error"``.
"""

import logging
import time
from collections.abc import Sequence

from tessera.core.claim import Claim
from tessera.core.finding import Finding, Reliability, Status
from tessera.core.media import Media
from tessera.core.module import Module
from tessera.core.registry import discover_modules

logger = logging.getLogger(__name__)


def _error_finding(module_id: str, note: str, runtime_ms: int) -> Finding:
    return Finding(
        module_id=module_id,
        status=Status.CANNOT_DETERMINE,
        confidence_low=0.0,
        confidence_high=0.0,
        summary="This check could not be completed.",
        reasoning=f"The module encountered an error and was isolated: {note}",
        reliability=Reliability.ERROR,
        reliability_note=note[:500],
        artifacts={},
        runtime_ms=runtime_ms,
    )


def run_all(
    media: Media,
    claim: Claim | None = None,
    modules: Sequence[Module] | None = None,
) -> list[Finding]:
    """Run all applicable modules in deterministic (id-sorted) order."""
    active_claim = claim if claim is not None else Claim()
    mods: list[Module] = (
        sorted(list(modules), key=lambda m: m.id) if modules is not None else discover_modules()
    )
    findings: list[Finding] = []
    for mod in mods:
        start = time.perf_counter()
        try:
            decision = mod.applicable(media, active_claim)
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.exception("Module %s applicable() failed", mod.id)
            findings.append(_error_finding(mod.id, f"applicability check failed: {exc}", elapsed))
            continue
        if not decision.applicable:
            continue
        try:
            findings.append(mod.run(media, active_claim))
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.exception("Module %s run() failed", mod.id)
            findings.append(_error_finding(mod.id, f"run failed: {exc}", elapsed))
    return findings
