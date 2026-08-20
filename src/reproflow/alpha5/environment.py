from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EnvironmentFingerprint:
    python: str
    implementation: str
    os: str
    machine: str
    executable: str
    dependencies: dict[str, str]
    lock_files: dict[str, str]
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


LOCK_FILES = (
    "pyproject.toml",
    "uv.lock",
    "poetry.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "Pipfile.lock",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _installed_dependencies() -> dict[str, str]:
    packages: dict[str, str] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            packages[name.lower()] = dist.version
    return dict(sorted(packages.items()))


def build_environment_fingerprint(repo: str | Path = ".") -> EnvironmentFingerprint:
    root = Path(repo).resolve()
    lock_files = {
        name: _sha256_file(root / name)
        for name in LOCK_FILES
        if (root / name).is_file()
    }
    base = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "executable": sys.executable,
        "dependencies": _installed_dependencies(),
        "lock_files": lock_files,
    }
    canonical = json.dumps(base, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return EnvironmentFingerprint(**base, fingerprint=fingerprint)


def write_environment_fingerprint(repo: str | Path, output: str | Path) -> EnvironmentFingerprint:
    result = build_environment_fingerprint(repo)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
