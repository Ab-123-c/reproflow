from reproflow.capsule.schema import FailureExpectation
from reproflow.sandbox.models import ExecutionEvidence
from reproflow.verifier.verifier import match_failure


def evidence(
    exit_code: int = 1,
    stderr: str = "UnicodeEncodeError: boom\n",
    stdout: str = "",
) -> ExecutionEvidence:
    return ExecutionEvidence(
        command="python repro.py",
        exit_code=exit_code,
        stdout=stdout,
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


def test_exception_class_matches_detected_traceback_type() -> None:
    expected = FailureExpectation(type="exception", exception_class="UnicodeEncodeError")
    result = match_failure(expected, evidence())
    assert result.matched is True
    assert result.signature is not None
    assert result.signature.startswith("UnicodeEncodeError:")


def test_exception_class_rejects_unrelated_nonzero_exit() -> None:
    expected = FailureExpectation(type="exception", exception_class="UnicodeEncodeError")
    result = match_failure(expected, evidence(stderr="ValueError: wrong bug\n"))
    assert result.matched is False
    assert any("expected exception UnicodeEncodeError" in reason for reason in result.reasons)


def test_crash_signal_matches_conventional_linux_exit_status() -> None:
    expected = FailureExpectation(type="crash", signal=11)
    result = match_failure(expected, evidence(exit_code=139, stderr="Segmentation fault\n"))
    assert result.matched is True
    assert result.signature is not None
    assert result.signature.startswith("SIGSEGV:")


def test_wrong_crash_signal_does_not_match() -> None:
    expected = FailureExpectation(type="crash", signal=11)
    result = match_failure(expected, evidence(exit_code=137, stderr="Killed\n"))
    assert result.matched is False
    assert any("expected signal SIGSEGV" in reason for reason in result.reasons)


def test_nonzero_exit_remains_explicitly_broad() -> None:
    expected = FailureExpectation(type="nonzero_exit")
    assert match_failure(expected, evidence(exit_code=7, stderr="anything\n")).matched is True


def test_output_mismatch_matches_wrong_successful_output() -> None:
    expected = FailureExpectation(type="output_mismatch", stdout_equals="expected\n")
    result = match_failure(expected, evidence(exit_code=0, stderr="", stdout="actual\n"))
    assert result.matched is True


def test_output_mismatch_rejects_expected_output() -> None:
    expected = FailureExpectation(type="output_mismatch", stdout_equals="expected\n")
    result = match_failure(expected, evidence(exit_code=0, stderr="", stdout="expected\n"))
    assert result.matched is False
