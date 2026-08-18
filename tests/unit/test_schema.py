import pytest
from pydantic import ValidationError

from reproflow.capsule.schema import ReproSpec


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
