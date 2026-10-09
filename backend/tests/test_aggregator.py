"""(3) Aggregator produces the three-state report with agree/disagree lists."""

from tessera.core.aggregator import aggregate
from tessera.core.finding import Finding, Reliability, Status


def _finding(module_id: str, status: Status) -> Finding:
    return Finding(
        module_id=module_id,
        status=status,
        confidence_low=0.5,
        confidence_high=0.8,
        summary=f"{module_id} summary.",
        reasoning=f"{module_id} reasoning.",
        reliability=Reliability.OK,
        reliability_note="ok",
        artifacts={},
        runtime_ms=1,
    )


def test_aggregator_mixed_votes() -> None:
    report = aggregate(
        [
            _finding("a", Status.CONFIRMED),
            _finding("b", Status.SUSPICIOUS),
            _finding("c", Status.CANNOT_DETERMINE),
        ]
    )
    assert report.overall_status == Status.SUSPICIOUS
    assert report.confirmed == ["a"]
    assert report.suspicious == ["b"]
    assert report.undetermined == ["c"]
    assert report.total == 3


def test_aggregator_all_undetermined() -> None:
    report = aggregate([_finding("c", Status.CANNOT_DETERMINE)])
    assert report.overall_status == Status.CANNOT_DETERMINE


def test_aggregator_empty() -> None:
    report = aggregate([])
    assert report.overall_status == Status.CANNOT_DETERMINE
    assert report.total == 0
