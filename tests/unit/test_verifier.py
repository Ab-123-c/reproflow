from reproflow.capsule.schema import FailureExpectation
from reproflow.sandbox.models import ExecutionEvidence
from reproflow.verifier.verifier import match_failure


def evidence(exit_code: int = 1, stderr: str = "UnicodeEncodeError: boom\n") -> ExecutionEvidence:
    return ExecutionEvidence(
        command="python repro.py",
        exit_code=exit_code,
        stdout="",
        stderr=stderr,
        duration_ms=10,
        timed_out=False,
        environment_hash="abc",
    )


def test_expected_exception_matches() -> None:
    expected = FailureExpectation(type="exception", stderr_contains=["UnicodeEncodeError"])
    result = match_failure(expected, evidence())
    assert result.matched is True
    assert result.signature is not None


def test_wrong_error_does_not_match() -> None:
    expected = FailureExpectation(type="exception", stderr_contains=["UnicodeEncodeError"])
    result = match_failure(expected, evidence(stderr="ValueError: nope\n"))
    assert result.matched is False
