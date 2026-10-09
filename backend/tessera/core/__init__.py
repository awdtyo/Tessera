"""Core plug-in contract: media, claim, finding, module, registry, runner, aggregator."""

from tessera.core.aggregator import Report, aggregate
from tessera.core.claim import Claim
from tessera.core.finding import Applicability, Finding, Reliability, Status
from tessera.core.media import Media, MediaType
from tessera.core.module import Module
from tessera.core.registry import discover_modules
from tessera.core.runner import run_all

__all__ = [
    "Applicability",
    "Claim",
    "Finding",
    "Media",
    "MediaType",
    "Module",
    "Reliability",
    "Report",
    "Status",
    "aggregate",
    "discover_modules",
    "run_all",
]
