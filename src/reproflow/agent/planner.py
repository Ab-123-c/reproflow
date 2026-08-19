from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from reproflow.capsule.schema import Metadata, ReproSpec, RunSpec, Setup, VerificationPolicy
from reproflow.repo.context import build_repository_snapshot
from reproflow.sandbox.base import SandboxRunner
from reproflow.sandbox.docker import DockerSandboxRunner
from reproflow.verifier.verifier import Verifier

from .models import Attempt, AttemptHistory, PlanningResult
from .provider import AgentProvider


class ReproductionPlanner:
    """Bounded issue-to-experiment loop.

    The provider proposes experiments; Docker executes them; Verifier alone decides
    whether the target failure was reproduced.
    """

    def __init__(
        self,
        provider: AgentProvider,
        *,
        max_attempts: int = 5,
        repetitions: int = 3,
        required_failures: int | None = None,
        runner_factory: Callable[[Path], SandboxRunner] | None = None,
    ) -> None:
        if not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")
        if not 1 <= repetitions <= 20:
            raise ValueError("repetitions must be between 1 and 20")
        self.provider = provider
        self.max_attempts = max_attempts
        self.repetitions = repetitions
        self.required_failures = required_failures or repetitions
        if self.required_failures > repetitions:
            raise ValueError("required_failures cannot exceed repetitions")
        self.runner_factory = runner_factory or (lambda root: DockerSandboxRunner(source_root=root))

    def reproduce(self, *, repo_root: Path, issue_text: str) -> PlanningResult:
        repo_root = repo_root.resolve()
        repository = build_repository_snapshot(repo_root, issue_text=issue_text)
        bug = self.provider.parse_bug(issue_text, repository)
        history = AttemptHistory()
        verifier = Verifier(self.runner_factory(repo_root))

        for number in range(1, self.max_attempts + 1):
            decision = self.provider.next_decision(bug, repository, history)
            if decision.action == "needs_information":
                return PlanningResult(
                    status="NEEDS_INFORMATION",
                    bug_report=bug,
                    history=history,
                    message=decision.message,
                )
            if decision.action == "stop":
                return PlanningResult(
                    status="NOT_REPRODUCIBLE",
                    bug_report=bug,
                    history=history,
                    message=decision.message,
                )

            assert decision.experiment is not None
            spec = self._spec_for_experiment(
                bug_title=bug.title,
                install_command=repository.profile.install_command,
                experiment=decision.experiment,
            )
            verification = verifier.verify(spec)
            history.attempts.append(
                Attempt(number=number, experiment=decision.experiment, verification=verification)
            )
            if verification.reproduced:
                return PlanningResult(
                    status="VERIFIED",
                    bug_report=bug,
                    history=history,
                    message=f"Reproduced by {decision.experiment.id}",
                    final_spec=spec,
                    final_verification=verification,
                )

        return PlanningResult(
            status="NOT_REPRODUCIBLE",
            bug_report=bug,
            history=history,
            message=f"Experiment budget exhausted after {self.max_attempts} attempts",
        )

    def _spec_for_experiment(
        self, *, bug_title: str, install_command: str | None, experiment
    ) -> ReproSpec:
        setup_commands = [install_command] if install_command else []
        return ReproSpec.model_validate(
            {
                "schema": "reproflow/v1",
                "metadata": Metadata(id=_safe_id(experiment.id), title=bug_title),
                "setup": Setup(commands=setup_commands),
                "files": experiment.files,
                "run": RunSpec(
                    command=experiment.command,
                    timeout_seconds=experiment.timeout_seconds,
                ),
                "failure": experiment.expected_failure,
                "verification": VerificationPolicy(
                    repetitions=self.repetitions,
                    required_failures=self.required_failures,
                ),
            }
        )


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")
    return cleaned or "experiment"
