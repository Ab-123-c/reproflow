from __future__ import annotations

import json
from pathlib import Path

import yaml

from reproflow.agent.models import PlanningResult
from reproflow.capsule.schema import ReproSpec
from reproflow.report import render_verification_markdown, verification_payload


def write_repro_spec(spec: ReproSpec, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = spec.model_dump(by_alias=True, exclude_none=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def write_planning_result(result: PlanningResult, output_dir: Path) -> Path | None:
    """Write an evidence ledger and, on success, a runnable repro.yaml."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "bug-report.json").write_text(
        result.bug_report.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "attempts.json").write_text(
        result.history.model_dump_json(indent=2), encoding="utf-8"
    )
    summary = {
        "status": result.status,
        "message": result.message,
        "attempts": len(result.history.attempts),
        "stable_signature": (
            result.final_verification.stable_signature if result.final_verification else None
        ),
    }
    (output_dir / "result.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    verification = result.final_verification
    if verification is None and result.history.attempts:
        verification = result.history.attempts[-1].verification
    if verification is not None:
        (output_dir / "verification.json").write_text(
            json.dumps(
                verification_payload(verification, spec=result.final_spec),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (output_dir / "report.md").write_text(
            render_verification_markdown(
                verification,
                title=result.message or result.status,
            ),
            encoding="utf-8",
        )
    if result.final_spec is None:
        return None
    return write_repro_spec(result.final_spec, output_dir / "repro.yaml")
