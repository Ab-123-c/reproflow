from __future__ import annotations

from collections.abc import Iterable

from reproflow.issue.models import BugReport
from reproflow.repo.context import RepositorySnapshot

from .models import AttemptHistory, PlannerDecision
from .provider import AgentProvider, ProviderError


class ScriptedProvider(AgentProvider):
    """Deterministic provider for tests, demos, and provider contract development."""

    def __init__(self, bug: BugReport, decisions: Iterable[PlannerDecision]) -> None:
        self.bug = bug
        self._decisions = iter(decisions)

    def parse_bug(self, issue_text: str, repository: RepositorySnapshot) -> BugReport:
        return self.bug

    def next_decision(
        self,
        bug: BugReport,
        repository: RepositorySnapshot,
        history: AttemptHistory,
    ) -> PlannerDecision:
        try:
            return next(self._decisions)
        except StopIteration as exc:
            raise ProviderError("ScriptedProvider has no decisions left") from exc
