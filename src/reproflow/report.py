"""Human and machine readable evidence reports.

The report format intentionally contains the same deterministic verifier data that is
written to JSON.  It is suitable for CI artifacts and for attaching to an issue without
having to paste terminal output by hand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reproflow.verifier.models import VerificationResult


def verification_payload(result: VerificationResult) -> dict[str, Any]:
    """Return a stable, JSON-serialisable representation of verification evidence."""
    return result.model_dump(mode="json")


def write_verification_report(
    result: VerificationResult,
    output: Path,
    *,
    title: str | None = None,
    spec_path: Path | None = None,
) -> tuple[Path, Path]:
    """Write ``verification.json`` and a concise Markdown report into ``output``."""
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "verification.json"
    json_path.write_text(
        json.dumps(verification_payload(result), indent=2, ensure_ascii=False) + "\n",
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
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read verification JSON: {exc}") from exc
    try:
        return VerificationResult.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"Invalid verification JSON: {exc}") from exc
