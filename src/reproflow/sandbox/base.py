from __future__ import annotations

from typing import Protocol

from reproflow.capsule.schema import ReproSpec

from .models import ExecutionEvidence


class SandboxRunner(Protocol):
    def run_many(self, spec: ReproSpec, repetitions: int) -> list[ExecutionEvidence]: ...
