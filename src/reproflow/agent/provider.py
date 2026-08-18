from __future__ import annotations

from abc import ABC, abstractmethod

from reproflow.issue.models import BugReport
from reproflow.repo.context import RepositorySnapshot

from .models import AttemptHistory, PlannerDecision


class ProviderError(RuntimeError):
    pass


class AgentProvider(ABC):
    """Provider-neutral interface for bug understanding and experiment proposals.

    Provider output is a proposal only. It never decides whether a bug was reproduced.
    """

    @abstractmethod
    def parse_bug(self, issue_text: str, repository: RepositorySnapshot) -> BugReport:
        raise NotImplementedError

    @abstractmethod
    def next_decision(
        self,
        bug: BugReport,
        repository: RepositorySnapshot,
        history: AttemptHistory,
    ) -> PlannerDecision:
        raise NotImplementedError
