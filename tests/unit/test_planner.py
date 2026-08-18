from pathlib import Path

from reproflow.agent.fake_provider import ScriptedProvider
from reproflow.agent.models import Experiment, PlannerDecision
from reproflow.agent.planner import ReproductionPlanner
from reproflow.issue.models import BugReport
from reproflow.sandbox.models import ExecutionEvidence


class FakeRunner:
    def run_many(self, spec, repetitions):
        return [
            ExecutionEvidence(
                command=spec.run.command,
                exit_code=1,
                stdout="",
                stderr="UnicodeEncodeError: boom\n",
                duration_ms=1,
                timed_out=False,
                environment_hash="fake",
            )
            for _ in range(repetitions)
        ]


def _repo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python=">=3.11"\n[tool.pytest.ini_options]\n', encoding="utf-8"
    )


def test_scripted_experiment_completes_bounded_loop(tmp_path: Path) -> None:
    _repo(tmp_path)
    experiment = Experiment(
        id="unicode",
        hypothesis="Unicode input fails",
        files={".reproflow/experiments/unicode/repro_case.py": '"你".encode("ascii")'},
        command="python .reproflow/experiments/unicode/repro_case.py",
        expected_failure={"type": "exception", "stderr_contains": ["UnicodeEncodeError"]},
    )
    provider = ScriptedProvider(
        BugReport(title="unicode bug", description="fails on unicode"),
        [PlannerDecision(action="experiment", experiment=experiment)],
    )
    planner = ReproductionPlanner(provider, repetitions=3, runner_factory=lambda root: FakeRunner())
    result = planner.reproduce(repo_root=tmp_path, issue_text="fails on unicode")
    assert result.status == "VERIFIED"
    assert len(result.history.attempts) == 1
    assert result.final_spec is not None
    assert result.final_spec.schema_ == "reproflow/v1"
    assert result.final_verification is not None
    assert result.final_verification.successful_runs == 3


def test_needs_information_stops_without_executing(tmp_path: Path) -> None:
    _repo(tmp_path)
    bug = BugReport(title="unclear", description="sometimes fails")
    provider = ScriptedProvider(
        bug,
        [PlannerDecision(action="needs_information", message="Need the failing input")],
    )
    result = ReproductionPlanner(
        provider, runner_factory=lambda root: FakeRunner()
    ).reproduce(repo_root=tmp_path, issue_text="sometimes fails")
    assert result.status == "NEEDS_INFORMATION"
    assert not result.history.attempts
