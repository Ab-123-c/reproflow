from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .detector import detect_repository
from .models import RepositoryProfile

_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".repro", ".reproflow", "node_modules"}
_PRIORITY_NAMES = {"pyproject.toml", "requirements.txt", "pytest.ini", "conftest.py", "README.md"}


class RepositorySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: RepositoryProfile
    files: dict[str, str] = Field(default_factory=dict)
    truncated: bool = False


def build_repository_snapshot(
    root: Path,
    *,
    max_files: int = 40,
    max_total_chars: int = 80_000,
    max_file_chars: int = 12_000,
) -> RepositorySnapshot:
    root = root.resolve()
    profile = detect_repository(root)

    candidates: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        if path.name in _PRIORITY_NAMES or path.suffix == ".py":
            candidates.append(path)

    def priority(path: Path) -> tuple[int, int, str]:
        relative = path.relative_to(root)
        if path.name in _PRIORITY_NAMES:
            rank = 0
        elif relative.parts and relative.parts[0] in {"src", "tests"}:
            rank = 1
        else:
            rank = 2
        return (rank, len(relative.parts), str(relative))

    files: dict[str, str] = {}
    total = 0
    truncated = False
    for path in sorted(candidates, key=priority):
        if len(files) >= max_files or total >= max_total_chars:
            truncated = True
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(text) > max_file_chars:
            text = text[:max_file_chars] + "\n... [truncated by ReproFlow]\n"
            truncated = True
        remaining = max_total_chars - total
        if len(text) > remaining:
            text = text[:remaining] + "\n... [truncated by ReproFlow]\n"
            truncated = True
        files[str(path.relative_to(root))] = text
        total += len(text)

    return RepositorySnapshot(profile=profile, files=files, truncated=truncated)
