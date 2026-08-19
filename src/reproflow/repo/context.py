from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .detector import detect_repository
from .models import RepositoryProfile

_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".repro",
    ".reproflow",
    "node_modules",
}
_PRIORITY_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "pytest.ini",
    "conftest.py",
    "README.md",
}
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{2,}")
_STOP_TERMS = {
    "about",
    "actual",
    "after",
    "again",
    "against",
    "and",
    "are",
    "author",
    "before",
    "body",
    "bug",
    "can",
    "comment",
    "comments",
    "content",
    "could",
    "data",
    "does",
    "error",
    "expected",
    "failure",
    "following",
    "for",
    "from",
    "github",
    "has",
    "have",
    "https",
    "instructions",
    "into",
    "issue",
    "its",
    "labels",
    "loaded",
    "not",
    "only",
    "please",
    "repository",
    "repro",
    "reproduce",
    "reproduction",
    "source",
    "state",
    "that",
    "the",
    "then",
    "they",
    "this",
    "title",
    "treat",
    "untrusted",
    "was",
    "were",
    "when",
    "will",
    "with",
    "without",
    "you",
    "your",
}
_MAX_SELECTION_TERMS = 32


class RepositorySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: RepositoryProfile
    files: dict[str, str] = Field(default_factory=dict)
    truncated: bool = False
    selection_terms: list[str] = Field(default_factory=list)
    selection_scores: dict[str, int] = Field(default_factory=dict)
    candidate_count: int = 0


def build_repository_snapshot(
    root: Path,
    *,
    issue_text: str | None = None,
    max_files: int = 40,
    max_total_chars: int = 80_000,
    max_file_chars: int = 12_000,
    max_candidates: int = 1_000,
    max_scan_chars: int = 4_000,
) -> RepositorySnapshot:
    """Build a bounded repository snapshot, ranked by issue relevance when available.

    Selection is deterministic and never executes repository code. Project metadata files remain
    pinned near the front of the snapshot; Python source/test files are then ranked using path and
    bounded-content matches against terms extracted from the untrusted issue text.
    """
    if max_files < 1:
        raise ValueError("max_files must be at least 1")
    if max_total_chars < 1:
        raise ValueError("max_total_chars must be at least 1")
    if max_file_chars < 1:
        raise ValueError("max_file_chars must be at least 1")
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1")
    if max_scan_chars < 0:
        raise ValueError("max_scan_chars cannot be negative")

    root = root.resolve()
    profile = detect_repository(root)
    selection_terms = _extract_selection_terms(issue_text or "")

    candidates: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in relative.parts):
            continue
        if path.name in _PRIORITY_NAMES or path.suffix == ".py":
            candidates.append(path)

    candidates.sort(
        key=lambda path: _candidate_scan_key(
            path.relative_to(root),
            path,
            root,
            selection_terms,
        )
    )
    candidate_count = len(candidates)
    scan_truncated = candidate_count > max_candidates
    candidates = candidates[:max_candidates]

    ranked: list[tuple[int, Path, str]] = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative = path.relative_to(root)
        score = _score_candidate(
            relative,
            text[:max_scan_chars] if max_scan_chars else "",
            selection_terms,
        )
        ranked.append((score, path, text))

    ranked.sort(
        key=lambda item: (
            -item[0],
            *_structural_key(item[1], root),
        )
    )

    files: dict[str, str] = {}
    selection_scores: dict[str, int] = {}
    total = 0
    truncated = scan_truncated

    for score, path, original_text in ranked:
        if len(files) >= max_files or total >= max_total_chars:
            truncated = True
            break

        text = original_text
        if len(text) > max_file_chars:
            text = text[:max_file_chars] + "\n... [truncated by ReproFlow]\n"
            truncated = True

        remaining = max_total_chars - total
        if remaining <= 0:
            truncated = True
            break
        if len(text) > remaining:
            text = text[:remaining] + "\n... [truncated by ReproFlow]\n"
            truncated = True

        relative_name = str(path.relative_to(root))
        files[relative_name] = text
        selection_scores[relative_name] = score
        total += len(text)

    return RepositorySnapshot(
        profile=profile,
        files=files,
        truncated=truncated,
        selection_terms=selection_terms,
        selection_scores=selection_scores,
        candidate_count=candidate_count,
    )


def _extract_selection_terms(issue_text: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(issue_text):
        token = match.group(0).lower().strip(".-")
        if len(token) < 3 or token in _STOP_TERMS or token.isdigit():
            continue
        variants = [token]
        if token.endswith(".py") and len(token) > 3:
            variants.append(token[:-3])
        for variant in variants:
            if variant and variant not in seen:
                seen.add(variant)
                terms.append(variant)
                if len(terms) >= _MAX_SELECTION_TERMS:
                    return terms
    return terms


def _score_candidate(relative: Path, sample: str, terms: list[str]) -> int:
    name = relative.name.lower()
    stem = relative.stem.lower()
    path_text = str(relative).lower()
    sample_text = sample.lower()

    if relative.name in _PRIORITY_NAMES:
        score = 10_000
    elif relative.parts and relative.parts[0] == "tests":
        score = 250
    elif relative.parts and relative.parts[0] == "src":
        score = 225
    elif len(relative.parts) == 1:
        score = 175
    else:
        score = 100

    for term in terms:
        if term == name or term == stem:
            score += 500
        elif term in path_text:
            score += 140

        if sample_text:
            occurrences = sample_text.count(term)
            if occurrences:
                score += min(occurrences, 5) * 12

    return score


def _candidate_scan_key(
    relative: Path,
    path: Path,
    root: Path,
    terms: list[str],
) -> tuple[int, int, int, str]:
    structural_rank, depth, name = _structural_key(path, root)
    return (structural_rank, -_path_relevance(relative, terms), depth, name)


def _path_relevance(relative: Path, terms: list[str]) -> int:
    name = relative.name.lower()
    stem = relative.stem.lower()
    path_text = str(relative).lower()
    score = 0
    for term in terms:
        if term == name or term == stem:
            score += 500
        elif term in path_text:
            score += 140
    return score


def _structural_key(path: Path, root: Path) -> tuple[int, int, str]:
    relative = path.relative_to(root)
    if path.name in _PRIORITY_NAMES:
        rank = 0
    elif relative.parts and relative.parts[0] in {"src", "tests"}:
        rank = 1
    else:
        rank = 2
    return (rank, len(relative.parts), str(relative))
