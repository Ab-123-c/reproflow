import pytest
from pydantic import ValidationError

from reproflow.capsule.schema import FailureExpectation, ReproSpec


def _base() -> dict:
    return {
        "schema": "reproflow/v1",
        "metadata": {"id": "x", "title": "demo"},
        "files": {"repro.py": "raise RuntimeError('boom')"},
        "run": {"command": "python repro.py"},
        "failure": {"type": "exception", "stderr_contains": ["RuntimeError"]},
    }


def test_schema_accepts_valid_capsule() -> None:
    spec = ReproSpec.model_validate(_base())
    assert spec.schema_ == "reproflow/v1"
    assert spec.verification.repetitions == 3


def test_required_failures_must_fit_repetitions() -> None:
    data = _base()
    data["verification"] = {"repetitions": 2, "required_failures": 3}
    with pytest.raises(ValidationError):
        ReproSpec.model_validate(data)


def test_exception_failure_requires_target_discriminator() -> None:
    with pytest.raises(ValidationError, match="exception failures require"):
        FailureExpectation(type="exception")


def test_exception_class_is_accepted_as_target_discriminator() -> None:
    expected = FailureExpectation(type="exception", exception_class="UnicodeEncodeError")
    assert expected.exception_class == "UnicodeEncodeError"


def test_crash_failure_requires_target_discriminator() -> None:
    with pytest.raises(ValidationError, match="crash failures require"):
        FailureExpectation(type="crash")


def test_signal_is_only_valid_for_crash() -> None:
    with pytest.raises(ValidationError, match="signal is only valid"):
        FailureExpectation(type="nonzero_exit", signal=11)


def test_output_mismatch_requires_comparison_rule() -> None:
    with pytest.raises(ValidationError, match="output_mismatch failures require"):
        FailureExpectation(type="output_mismatch")


def test_capsule_rejects_unsafe_file_paths() -> None:
    data = _base()
    data["files"] = {"../escape.py": "pass"}
    with pytest.raises(ValidationError, match="unsafe capsule file path"):
        ReproSpec.model_validate(data)


@pytest.mark.parametrize("path", [".", "repro.py/", "a\\b.py"])
def test_capsule_rejects_directory_or_windows_paths(path: str) -> None:
    data = _base()
    data["files"] = {path: "pass"}
    with pytest.raises(ValidationError, match="unsafe capsule file path"):
        ReproSpec.model_validate(data)


def test_environment_variables_are_supported() -> None:
    data = _base()
    data["environment"] = {"variables": {"LC_ALL": "C.UTF-8"}}
    spec = ReproSpec.model_validate(data)
    assert spec.environment.variables["LC_ALL"] == "C.UTF-8"
