from __future__ import annotations

import hashlib
import re

from reproflow.capsule.schema import FailureExpectation, ReproSpec
from reproflow.sandbox.base import SandboxRunner
from reproflow.sandbox.models import ExecutionEvidence

from .models import RunVerification, VerificationResult


class Verifier:
    def __init__(self, runner: SandboxRunner) -> None:
        self.runner = runner

    def verify(self, spec: ReproSpec) -> VerificationResult:
        evidence_runs = self.runner.run_many(spec, spec.verification.repetitions)
        runs = [match_failure(spec.failure, evidence) for evidence in evidence_runs]

        successful = sum(run.matched for run in runs)
        signatures = [run.signature for run in runs if run.matched and run.signature]
        stable_signature = signatures[0] if signatures and len(set(signatures)) == 1 else None

        return VerificationResult(
            reproduced=successful >= spec.verification.required_failures,
            successful_runs=successful,
            total_runs=len(runs),
            stable_signature=stable_signature,
            runs=runs,
        )


def match_failure(expectation: FailureExpectation, evidence: ExecutionEvidence) -> RunVerification:
    reasons: list[str] = []

    if expectation.type == "timeout":
        matched_type = evidence.timed_out
        if not matched_type:
            reasons.append("process did not time out")
    elif expectation.type in {"exception", "crash", "nonzero_exit", "output_mismatch"}:
        matched_type = (not evidence.timed_out) and evidence.exit_code not in (None, 0)
        if not matched_type:
            reasons.append(f"expected a non-zero exit, got {evidence.exit_code}")
    else:
        matched_type = False
        reasons.append(f"unsupported failure type: {expectation.type}")

    if expectation.exit_code is not None and evidence.exit_code != expectation.exit_code:
        reasons.append(f"expected exit code {expectation.exit_code}, got {evidence.exit_code}")

    for token in expectation.stdout_contains:
        if token not in evidence.stdout:
            reasons.append(f"stdout missing expected text: {token!r}")

    for token in expectation.stderr_contains:
        if token not in evidence.stderr:
            reasons.append(f"stderr missing expected text: {token!r}")

    matched = matched_type and not reasons
    return RunVerification(
        matched=matched,
        reasons=reasons,
        signature=_signature(expectation, evidence) if matched else None,
        evidence=evidence,
    )


def _signature(expectation: FailureExpectation, evidence: ExecutionEvidence) -> str:
    exception_name = None
    if expectation.type == "exception":
        matches = re.findall(r"(?:^|\n)([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception))(?::|\n|$)", evidence.stderr)
        if matches:
            exception_name = matches[-1]

    normalized = "\n".join(
        [
            expectation.type,
            exception_name or "",
            str(evidence.exit_code),
            "|".join(expectation.stdout_contains),
            "|".join(expectation.stderr_contains),
        ]
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    human = exception_name or expectation.type
    return f"{human}:{digest}"
