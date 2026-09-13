"""Human and machine readable evidence reports.

The report format intentionally contains the same deterministic verifier data that is
written to JSON.  It is suitable for CI artifacts and for attaching to an issue without
having to paste terminal output by hand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reproflow.capsule.schema import ReproSpec
from reproflow.verifier.models import VerificationResult


def verification_payload(
    result: VerificationResult,
    *,
    spec: ReproSpec | None = None,
) -> dict[str, Any]:
    """Return a stable, JSON-serialisable representation of verification evidence."""
    payload = result.model_dump(mode="json", exclude_none=True)
    payload["format"] = "reproflow/evidence/v1"
    payload["status"] = "verified" if result.reproduced else "not_reproduced"
    payload["repetitions"] = {
        "required": spec.verification.required_failures if spec else result.total_runs,
        "successful": result.successful_runs,
        "total": result.total_runs,
    }
    payload["execution"] = {
        "runs": result.total_runs,
        "matched_runs": result.successful_runs,
        "timed_out_runs": sum(run.evidence.timed_out for run in result.runs),
    }
    if spec is not None:
        failure = spec.failure.model_dump(mode="json", exclude_none=True)
        payload["failure"] = failure
        payload["environment"] = {
            "image": spec.environment.image,
            "variables": spec.environment.variables,
            "hashes": sorted({run.evidence.environment_hash for run in result.runs}),
        }
    return payload


def write_verification_report(
    result: VerificationResult,
    output: Path,
    *,
    title: str | None = None,
    spec_path: Path | None = None,
    spec: ReproSpec | None = None,
) -> tuple[Path, Path]:
    """Write ``verification.json`` and a concise Markdown report into ``output``."""
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "verification.json"
    json_path.write_text(
        json.dumps(verification_payload(result, spec=spec), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    markdown_path = output / "report.md"
    markdown_path.write_text(
        render_verification_markdown(result, title=title, spec_path=spec_path),
        encoding="utf-8",
    )
    return json_path, markdown_path


def render_verification_markdown(
    result: VerificationResult,
    *,
    title: str | None = None,
    spec_path: Path | None = None,
) -> str:
    status = "VERIFIED REPRODUCTION" if result.reproduced else "NOT REPRODUCED"
    lines = [f"# {title or status}", "", f"**Status:** `{status}`", ""]
    if spec_path is not None:
        lines.append(f"**Capsule:** `{spec_path}`")
        lines.append("")
    lines.extend(
        [
            f"**Repeatability:** {result.successful_runs}/{result.total_runs}",
            f"**Stable signature:** `{result.stable_signature or 'none'}`",
            "",
            "## Runs",
            "",
            "| Run | Match | Exit | Timeout | Duration | Signature |",
            "| ---: | :---: | ---: | :---: | ---: | --- |",
        ]
    )
    for index, run in enumerate(result.runs, start=1):
        evidence = run.evidence
        exit_code = "timeout" if evidence.timed_out else str(evidence.exit_code)
        lines.append(
            f"| {index} | {'yes' if run.matched else 'no'} | {exit_code} | "
            f"{'yes' if evidence.timed_out else 'no'} | {evidence.duration_ms} ms | "
            f"`{run.signature or ''}` |"
        )
    for index, run in enumerate(result.runs, start=1):
        if run.matched:
            continue
        lines.extend(["", f"### Run {index} diagnostics", ""])
        if run.reasons:
            lines.extend(f"- {reason}" for reason in run.reasons)
        stdout = _tail(run.evidence.stdout)
        stderr = _tail(run.evidence.stderr)
        if stdout:
            lines.extend(["", "```text", "stdout:", stdout, "```"])
        if stderr:
            lines.extend(["", "```text", "stderr:", stderr, "```"])
    return "\n".join(lines).rstrip() + "\n"


def _tail(value: str, limit: int = 4_000) -> str:
    if len(value) <= limit:
        return value.rstrip()
    return "... [tail truncated by ReproFlow]\n" + value[-limit:].rstrip()


def load_verification_result(path: Path) -> VerificationResult:
    """Load a previously persisted verifier result from a JSON file."""
    payload = load_verification_payload(path)
    try:
        return VerificationResult.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"Invalid verification JSON: {exc}") from exc


def load_verification_payload(path: Path) -> dict[str, Any]:
    """Load raw evidence JSON while preserving the v1 extension fields."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read verification JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid verification JSON: expected an object")
    return payload


def validate_evidence_payload(payload: dict[str, Any]) -> list[str]:
    """Return consistency errors for a ``reproflow/evidence/v1`` document."""
    errors: list[str] = []
    if payload.get("format") != "reproflow/evidence/v1":
        errors.append("format must be reproflow/evidence/v1")
    status = payload.get("status")
    if status not in {"verified", "not_reproduced"}:
        errors.append("status must be verified or not_reproduced")
    reproduced = payload.get("reproduced")
    if not isinstance(reproduced, bool):
        errors.append("reproduced must be a boolean")
    elif (status == "verified") != reproduced:
        errors.append("status and reproduced disagree")
    successful = payload.get("successful_runs")
    total = payload.get("total_runs")
    if not isinstance(successful, int) or not isinstance(total, int):
        errors.append("successful_runs and total_runs must be integers")
    elif successful < 0 or total < 1 or successful > total:
        errors.append("run counts must satisfy 0 <= successful_runs <= total_runs")
    runs = payload.get("runs")
    if not isinstance(runs, list):
        errors.append("runs must be an array")
    elif isinstance(total, int) and len(runs) != total:
        errors.append("runs length must equal total_runs")
    repetitions = payload.get("repetitions")
    if not isinstance(repetitions, dict):
        errors.append("repetitions must be an object")
    else:
        if repetitions.get("successful") != successful:
            errors.append("repetitions.successful must equal successful_runs")
        if repetitions.get("total") != total:
            errors.append("repetitions.total must equal total_runs")
    execution = payload.get("execution")
    if not isinstance(execution, dict):
        errors.append("execution must be an object")
    else:
        if execution.get("runs") != total:
            errors.append("execution.runs must equal total_runs")
        if execution.get("matched_runs") != successful:
            errors.append("execution.matched_runs must equal successful_runs")
    return errors
