from pathlib import Path

import pytest

from reproflow.capsule.loader import load_repro_spec
from reproflow.sandbox.docker import DockerSandboxRunner, DockerUnavailableError
from reproflow.verifier.verifier import Verifier


def test_unicode_demo_end_to_end() -> None:
    root = Path(__file__).resolve().parents[2]
    spec = load_repro_spec(root / "examples" / "unicode-username" / "repro.yaml")
    runner = DockerSandboxRunner()
    try:
        runner.check_available()
    except DockerUnavailableError:
        pytest.skip("Docker is not available")
    result = Verifier(runner).verify(spec)
    assert result.reproduced is True
    assert result.successful_runs == 3
