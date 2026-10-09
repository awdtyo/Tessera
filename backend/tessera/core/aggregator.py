"""Aggregator: merges findings into one three-state report.

Never relies on one signal: the report lists which modules agreed and
disagreed. Wording avoids verdicts ("fake"/"real"); uncertainty is kept.
"""

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from tessera.core.finding import Finding, Status


class Report(BaseModel):
    """Mosaic view over per-module findings."""

    model_config = ConfigDict(frozen=True)

    overall_status: Status
    summary: str
    confirmed: list[str] = Field(default_factory=list)
    suspicious: list[str] = Field(default_factory=list)
    undetermined: list[str] = Field(default_factory=list)
    total: int = Field(ge=0)


def aggregate(findings: Sequence[Finding]) -> Report:
    """Merge findings deterministically into a Report."""
    confirmed = sorted(f.module_id for f in findings if f.status == Status.CONFIRMED)
    suspicious = sorted(f.module_id for f in findings if f.status == Status.SUSPICIOUS)
    undetermined = sorted(f.module_id for f in findings if f.status == Status.CANNOT_DETERMINE)

    if suspicious:
        overall = Status.SUSPICIOUS
        summary = (
            f"Found signs consistent with editing in {len(suspicious)} "
            f"of {len(findings)} signal(s); "
            f"{len(confirmed)} supported authenticity, "
            f"{len(undetermined)} could not be determined."
        )
    elif confirmed:
        overall = Status.CONFIRMED
        summary = (
            f"{len(confirmed)} of {len(findings)} signal(s) support authenticity; "
            f"{len(undetermined)} could not be determined and none raised concerns."
        )
    else:
        overall = Status.CANNOT_DETERMINE
        if not findings:
            summary = "No applicable checks ran, so nothing could be determined."
        else:
            summary = (
                f"All {len(findings)} signal(s) were inconclusive; "
                "absence of evidence is not contradiction."
            )
    return Report(
        overall_status=overall,
        summary=summary,
        confirmed=confirmed,
        suspicious=suspicious,
        undetermined=undetermined,
        total=len(findings),
    )
