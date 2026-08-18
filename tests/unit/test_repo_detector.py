from pathlib import Path

from reproflow.repo.detector import detect_repository


def test_detects_python_pytest_repo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.11"\n[tool.pytest.ini_options]\n',
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("", encoding="utf-8")
    profile = detect_repository(tmp_path)
    assert profile.language == "Python"
    assert profile.python_version == ">=3.11"
    assert profile.package_manager == "uv"
    assert profile.test_framework == "pytest"
    assert profile.test_command == "uv run pytest"
