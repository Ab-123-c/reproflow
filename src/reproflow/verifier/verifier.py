from __future__ import annotations

import hashlib
import re
import signal as signal_module

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
    actual_exception = _extract_exception_name(evidence.stderr)
    actual_signal = _signal_from_exit_code(evidence.exit_code)

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

    if expectation.exception_class is not None:
        expected_name = expectation.exception_class.rsplit(".", 1)[-1]
        if actual_exception != expected_name:
            actual_label = actual_exception or "none detected"
            reasons.append(
                f"expected exception {expectation.exception_class}, got {actual_label}"
            )

    if expectation.signal is not None and actual_signal != expectation.signal:
        reasons.append(
            f"expected signal {_signal_label(expectation.signal)}, "
            f"got {_signal_label(actual_signal) if actual_signal is not None else 'none detected'}"
        )

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
        signature=(
            _signature(
                expectation,
                evidence,
                actual_exception=actual_exception,
                actual_signal=actual_signal,
            )
            if matched
            else None
        ),
        evidence=evidence,
    )


def _extract_exception_name(stderr: str) -> str | None:
    matches = re.findall(
        r"(?:^|\n)([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Warning))(?::|\n|$)",
        stderr,
    )
    return matches[-1] if matches else None


def _signal_from_exit_code(exit_code: int | None) -> int | None:
    if exit_code is None or exit_code == 0:
        return None
    if exit_code < 0:
        return -exit_code
    if 129 <= exit_code <= 192:
        return exit_code - 128
    return None


def _signal_label(number: int) -> str:
    try:
        return f"SIG{signal_module.Signals(number).name.removeprefix('SIG')} ({number})"
    except ValueError:
        return f"signal {number}"


def _signature(
    expectation: FailureExpectation,
    evidence: ExecutionEvidence,
    *,
    actual_exception: str | None,
    actual_signal: int | None,
) -> str:
    normalized = "\n".join(
        [
            expectation.type,
            actual_exception or "",
            str(actual_signal or ""),
            str(evidence.exit_code),
            expectation.exception_class or "",
            str(expectation.signal or ""),
            "|".join(expectation.stdout_contains),
            "|".join(expectation.stderr_contains),
        ]
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    if actual_exception:
        human = actual_exception
    elif actual_signal is not None:
        human = _signal_label(actual_signal).split(" ", 1)[0]
    else:
        human = expectation.type
    return f"{human}:{digest}"
