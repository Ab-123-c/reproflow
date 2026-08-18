from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from reproflow.capsule.schema import FailureExpectation, ReproSpec
from reproflow.issue.models import BugReport
from reproflow.verifier.models import VerificationResult


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Experiment(StrictModel):
    id: str
    hypothesis: str
    files: dict[str, str] = Field(default_factory=dict)
    command: str
    expected_failure: FailureExpectation
    timeout_seconds: int = Field(default=60, ge=1, le=300)

    @model_validator(mode="after")
    def generated_files_live_in_experiment_namespace(self) -> "Experiment":
        for relative in self.files:
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"unsafe experiment file path: {relative}")
            if len(path.parts) < 3 or path.parts[:2] != (".reproflow", "experiments"):
                raise ValueError(
                    "experiment files must live under .reproflow/experiments/ to avoid modifying source"
                )
        return self


class PlannerDecision(StrictModel):
    action: Literal["experiment", "needs_information", "stop"]
    experiment: Experiment | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_action_payload(self) -> "PlannerDecision":
        if self.action == "experiment" and self.experiment is None:
            raise ValueError("experiment action requires an experiment")
        if self.action != "experiment" and self.experiment is not None:
            raise ValueError("non-experiment action cannot include an experiment")
        if self.action in {"needs_information", "stop"} and not self.message:
            raise ValueError(f"{self.action} action requires a message")
        return self


class Attempt(StrictModel):
    number: int
    experiment: Experiment
    verification: VerificationResult


class AttemptHistory(StrictModel):
    attempts: list[Attempt] = Field(default_factory=list)

    def compact_text(self, max_output_chars: int = 3000) -> str:
        if not self.attempts:
            return "No experiments have been attempted yet."
        chunks: list[str] = []
        for attempt in self.attempts:
            verification = attempt.verification
            lines = [
                f"Attempt {attempt.number}: {attempt.experiment.id}",
                f"Hypothesis: {attempt.experiment.hypothesis}",
                f"Command: {attempt.experiment.command}",
                f"Matched runs: {verification.successful_runs}/{verification.total_runs}",
            ]
            if verification.stable_signature:
                lines.append(f"Stable signature: {verification.stable_signature}")
            for index, run in enumerate(verification.runs, start=1):
                stdout = run.evidence.stdout[-max_output_chars:]
                stderr = run.evidence.stderr[-max_output_chars:]
                lines.extend(
                    [
                        f"Run {index} exit={run.evidence.exit_code} timeout={run.evidence.timed_out}",
                        f"stdout tail:\n{stdout}",
                        f"stderr tail:\n{stderr}",
                    ]
                )
            chunks.append("\n".join(lines))
        return "\n\n".join(chunks)


class PlanningResult(StrictModel):
    status: Literal["VERIFIED", "NOT_REPRODUCIBLE", "NEEDS_INFORMATION"]
    bug_report: BugReport
    history: AttemptHistory
    message: str | None = None
    final_spec: ReproSpec | None = None
    final_verification: VerificationResult | None = None
