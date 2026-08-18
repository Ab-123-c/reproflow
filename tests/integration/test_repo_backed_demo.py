from pathlib import Path

import pytest

from reproflow.capsule.loader import load_repro_spec
from reproflow.sandbox.docker import DockerSandboxRunner, DockerUnavailableError
from reproflow.verifier.verifier import Verifier


def test_repo_backed_reproduction() -> None:
    root = Path(__file__).resolve().parents[2]
    demo = root / "examples" / "planner-demo"
    spec = load_repro_spec(demo / "repro.yaml")
    runner = DockerSandboxRunner(source_root=demo)
    try:
        runner.check_available()
    except DockerUnavailableError:
        pytest.skip("Docker is not available")
    result = Verifier(runner).verify(spec)
    assert result.reproduced is True
    assert result.successful_runs == 3
