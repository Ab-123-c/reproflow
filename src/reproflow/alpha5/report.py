from __future__ import annotations

from .environment import EnvironmentFingerprint
from .history import RunRecord
from .score import ReproScore


def render_run_report(
    record: RunRecord,
    *,
    score: ReproScore | None = None,
    environment: EnvironmentFingerprint | None = None,
) -> str:
    lines = [
        f"# ReproFlow run {record.run_id}",
        "",
        f"- **Issue:** {record.issue}",
        f"- **Status:** {record.status.value}",
        f"- **Runs:** {record.successful_runs}/{record.runs}",
    ]
    if record.failure_signature:
        lines.append(f"- **Failure signature:** `{record.failure_signature}`")
    if score:
        lines += [
            f"- **Repro Score:** {score.total}/100",
            "",
            "## Score breakdown",
            "",
            f"- Repeatability: {score.repeatability}/30",
            f"- Minimality: {score.minimality}/20",
            f"- Environment lock: {score.environment_lock}/20",
            f"- Failure precision: {score.failure_precision}/20",
            f"- Portability: {score.portability}/10",
        ]
    if environment:
        lines += [
            "",
            "## Environment",
            "",
            f"- Python: {environment.python}",
            f"- OS: {environment.os}",
            f"- Machine: {environment.machine}",
            f"- Fingerprint: `{environment.fingerprint}`",
        ]
    lines.append("")
    return "\n".join(lines)
