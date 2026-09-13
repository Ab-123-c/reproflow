"""Generate a dependency free SVG status badge for verification evidence."""

from __future__ import annotations

from html import escape
from pathlib import Path

from reproflow.verifier.models import VerificationResult


def render_badge(
    result: VerificationResult,
    *,
    label: str = "ReproFlow",
    verified_text: str = "Verified",
    failed_text: str = "Not verified",
) -> str:
    message = verified_text if result.reproduced else failed_text
    color = "#2da44e" if result.reproduced else "#6e7781"
    left = max(58, len(label) * 7 + 16)
    right = max(72, len(message) * 7 + 16)
    width = left + right
    aria = escape(f"{label}: {message}", quote=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" '
        f'role="img" aria-label="{aria}">'
        f'<title>{aria}</title><rect width="{left}" height="20" fill="#555"/>'
        f'<rect x="{left}" width="{right}" height="20" fill="{color}"/>'
        f'<text x="{left / 2:.1f}" y="14" fill="#fff" text-anchor="middle" '
        f'font-family="Verdana,sans-serif" font-size="11">{escape(label)}</text>'
        f'<text x="{left + right / 2:.1f}" y="14" fill="#fff" text-anchor="middle" '
        f'font-family="Verdana,sans-serif" font-size="11">{escape(message)}</text></svg>\n'
    )


def write_badge(result: VerificationResult, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_badge(result), encoding="utf-8")
    return output
