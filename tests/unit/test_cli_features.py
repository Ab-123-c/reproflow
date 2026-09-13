from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from reproflow.cli import app
from reproflow.capsule.loader import load_repro_spec
from reproflow.report import write_verification_report
from reproflow.sandbox.models import ExecutionEvidence
from reproflow.verifier.models import RunVerification, VerificationResult


runner = CliRunner()


def test_init_creates_valid_capsule(tmp_path: Path) -> None:
    path = tmp_path / "repro.yaml"
    result = runner.invoke(app, ["init", str(path), "--id", "demo", "--title", "Demo"])
    assert result.exit_code == 0, result.stdout
    spec = load_repro_spec(path)
    assert spec.metadata.id == "demo"
    assert "repro.py" in spec.files


def test_validate_json_is_machine_readable() -> None:
    spec_path = Path(__file__).resolve().parents[2] / "examples" / "unicode-username" / "repro.yaml"
    result = runner.invoke(app, ["validate", str(spec_path), "--json"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["schema"] == "reproflow/v1"


def test_report_command_reads_persisted_verification(tmp_path: Path) -> None:
    evidence = ExecutionEvidence(
        command="python repro.py",
        exit_code=1,
        stdout="",
        stderr="RuntimeError: boom\n",
        duration_ms=2,
        timed_out=False,
        environment_hash="abc",
    )
    verification = VerificationResult(
        reproduced=True,
        successful_runs=1,
        total_runs=1,
        stable_signature="RuntimeError:abc",
        runs=[RunVerification(matched=True, signature="RuntimeError:abc", evidence=evidence)],
    )
    write_verification_report(verification, tmp_path)
    result = runner.invoke(app, ["report", str(tmp_path)])
    assert result.exit_code == 0, result.stdout
    assert "VERIFIED REPRODUCTION" in result.stdout
