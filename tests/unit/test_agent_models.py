import pytest
from pydantic import ValidationError

from reproflow.agent.models import Experiment, PlannerDecision


def experiment() -> Experiment:
    return Experiment(
        id="exp-1",
        hypothesis="Unicode input triggers the target error",
        files={".reproflow/experiments/unicode/repro_case.py": '"你".encode("ascii")'},
        command="python .reproflow/experiments/unicode/repro_case.py",
        expected_failure={"type": "exception", "stderr_contains": ["UnicodeEncodeError"]},
    )


def test_planner_decision_requires_experiment_payload() -> None:
    with pytest.raises(ValidationError):
        PlannerDecision(action="experiment")


def test_planner_decision_accepts_experiment() -> None:
    decision = PlannerDecision(action="experiment", experiment=experiment())
    assert decision.experiment is not None


def test_experiment_cannot_write_into_source_tree() -> None:
    with pytest.raises(ValidationError):
        Experiment(
            id="bad",
            hypothesis="overwrite source",
            files={"src/package.py": "raise RuntimeError()"},
            command="python src/package.py",
            expected_failure={"type": "exception"},
        )
