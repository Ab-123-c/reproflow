from pathlib import Path

import pytest

from reproflow.repo.context import build_repository_snapshot


def _python_repo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="demo"\nrequires-python=">=3.11"\n', encoding="utf-8"
    )


def test_snapshot_is_bounded_and_skips_git(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hidden.py").write_text("SECRET = 1\n", encoding="utf-8")

    snapshot = build_repository_snapshot(tmp_path)

    assert "app.py" in snapshot.files
    assert all(not name.startswith(".git/") for name in snapshot.files)


def test_issue_terms_promote_relevant_source_file(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "aaa_misc.py").write_text("def helper():\n    return 1\n", encoding="utf-8")
    (tmp_path / "src" / "unicode_codec.py").write_text(
        "def decode_username(value):\n    return value.encode('ascii')\n",
        encoding="utf-8",
    )

    snapshot = build_repository_snapshot(
        tmp_path,
        issue_text="decode_username raises UnicodeEncodeError for Chinese usernames",
        max_files=2,
    )

    assert list(snapshot.files) == ["pyproject.toml", "src/unicode_codec.py"]
    assert snapshot.selection_scores["src/unicode_codec.py"] > 225


def test_issue_terms_can_match_file_content(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "alpha.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    (tmp_path / "src" / "worker.py").write_text(
        "def parse_emoji(payload):\n    raise UnicodeDecodeError('utf-8', b'x', 0, 1, 'bad')\n",
        encoding="utf-8",
    )

    snapshot = build_repository_snapshot(
        tmp_path,
        issue_text="parse_emoji crashes with UnicodeDecodeError",
        max_files=2,
    )

    assert list(snapshot.files) == ["pyproject.toml", "src/worker.py"]


def test_snapshot_records_bounded_selection_metadata(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    for index in range(5):
        (tmp_path / f"module_{index}.py").write_text(f"VALUE = {index}\n", encoding="utf-8")

    snapshot = build_repository_snapshot(
        tmp_path,
        issue_text="module_4 returns the wrong VALUE",
        max_files=3,
        max_candidates=4,
    )

    assert snapshot.candidate_count == 6
    assert snapshot.truncated is True
    assert len(snapshot.files) <= 3
    assert "module_4.py" in snapshot.files
    assert len(snapshot.selection_terms) <= 32


def test_snapshot_selection_is_deterministic(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    (tmp_path / "tests").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests" / "test_parser.py").write_text("def test_parser():\n    pass\n", encoding="utf-8")
    (tmp_path / "src" / "parser.py").write_text("def parser():\n    return None\n", encoding="utf-8")

    kwargs = {"issue_text": "parser failure", "max_files": 3}
    first = build_repository_snapshot(tmp_path, **kwargs)
    second = build_repository_snapshot(tmp_path, **kwargs)

    assert list(first.files) == list(second.files)
    assert first.selection_scores == second.selection_scores


def test_generated_reproflow_directory_is_not_selected(tmp_path: Path) -> None:
    _python_repo(tmp_path)
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    generated = tmp_path / ".reproflow" / "experiments"
    generated.mkdir(parents=True)
    (generated / "poison.py").write_text("SECRET = 'do not load'\n", encoding="utf-8")

    snapshot = build_repository_snapshot(tmp_path, issue_text="poison SECRET")

    assert all(not name.startswith(".reproflow/") for name in snapshot.files)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("max_files", 0),
        ("max_total_chars", 0),
        ("max_file_chars", 0),
        ("max_candidates", 0),
        ("max_scan_chars", -1),
    ],
)
def test_snapshot_rejects_invalid_bounds(tmp_path: Path, name: str, value: int) -> None:
    _python_repo(tmp_path)
    with pytest.raises(ValueError):
        build_repository_snapshot(tmp_path, **{name: value})
