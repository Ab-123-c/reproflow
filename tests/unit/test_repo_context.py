from pathlib import Path

from reproflow.repo.context import build_repository_snapshot


def test_snapshot_is_bounded_and_skips_git(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python=">=3.11"\n', encoding="utf-8")
    (tmp_path / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "hidden.py").write_text("SECRET = 1\n", encoding="utf-8")
    snapshot = build_repository_snapshot(tmp_path)
    assert "app.py" in snapshot.files
    assert all(not name.startswith(".git/") for name in snapshot.files)
