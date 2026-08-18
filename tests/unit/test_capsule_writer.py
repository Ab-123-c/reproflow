from pathlib import Path

from reproflow.agent.models import AttemptHistory, PlanningResult
from reproflow.capsule.writer import write_planning_result
from reproflow.issue.models import BugReport


def test_writer_persists_non_success_evidence(tmp_path: Path) -> None:
    result = PlanningResult(
        status="NOT_REPRODUCIBLE",
        bug_report=BugReport(title="x", description="x"),
        history=AttemptHistory(),
        message="budget exhausted",
    )
    repro = write_planning_result(result, tmp_path)
    assert repro is None
    assert (tmp_path / "bug-report.json").exists()
    assert (tmp_path / "attempts.json").exists()
    assert (tmp_path / "result.json").exists()
