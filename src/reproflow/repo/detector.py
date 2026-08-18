from __future__ import annotations

import re
from pathlib import Path

from .models import RepositoryProfile


def detect_repository(root: Path) -> RepositoryProfile:
    root = root.resolve()
    pyproject = root / "pyproject.toml"
    requirements = root / "requirements.txt"

    if not pyproject.exists() and not requirements.exists():
        raise ValueError("Unsupported repository: no pyproject.toml or requirements.txt found")

    package_manager = _detect_package_manager(root)
    test_framework = _detect_test_framework(root)

    return RepositoryProfile(
        root=str(root),
        language="Python",
        python_version=_detect_python_version(root),
        package_manager=package_manager,
        test_framework=test_framework,
        install_command=_install_command(package_manager),
        test_command=_test_command(package_manager, test_framework),
        important_files=_find_important_files(root),
    )


def _detect_package_manager(root: Path) -> str:
    if (root / "uv.lock").exists():
        return "uv"
    if (root / "poetry.lock").exists():
        return "poetry"
    return "pip"


def _detect_test_framework(root: Path) -> str | None:
    if (root / "pytest.ini").exists() or (root / "conftest.py").exists():
        return "pytest"
    tests = root / "tests"
    if tests.is_dir() and any(tests.rglob("test_*.py")):
        return "pytest"
    pyproject = root / "pyproject.toml"
    if pyproject.exists() and "pytest" in pyproject.read_text(encoding="utf-8", errors="ignore"):
        return "pytest"
    return None


def _detect_python_version(root: Path) -> str | None:
    version_file = root / ".python-version"
    if version_file.exists():
        value = version_file.read_text(encoding="utf-8").strip()
        return value or None

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', text)
        if match:
            return match.group(1)
    return None


def _install_command(package_manager: str) -> str:
    return {
        "uv": "uv sync",
        "poetry": "poetry install",
        "pip": "pip install -e .",
    }[package_manager]


def _test_command(package_manager: str, framework: str | None) -> str | None:
    if framework != "pytest":
        return None
    return {
        "uv": "uv run pytest",
        "poetry": "poetry run pytest",
        "pip": "pytest",
    }[package_manager]


def _find_important_files(root: Path) -> list[str]:
    candidates = [
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "requirements.txt",
        "pytest.ini",
        "conftest.py",
        "README.md",
    ]
    return [name for name in candidates if (root / name).exists()]
