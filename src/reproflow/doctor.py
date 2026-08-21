from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DoctorReport:
    python_version: str
    python_supported: bool
    docker_cli: bool
    docker_daemon: bool
    docker_version: str | None
    openai_package: bool
    openai_api_key: bool
    github_token: bool

    @property
    def runtime_ready(self) -> bool:
        return self.python_supported and self.docker_cli and self.docker_daemon

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["runtime_ready"] = self.runtime_ready
        return data


def collect_doctor_report() -> DoctorReport:
    python_supported = sys.version_info >= (3, 11)
    docker_path = shutil.which("docker")
    docker_daemon = False
    docker_version: str | None = None

    if docker_path:
        try:
            completed = subprocess.run(
                [docker_path, "version", "--format", "{{.Server.Version}}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if completed.returncode == 0:
                docker_daemon = True
                docker_version = completed.stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            pass

    return DoctorReport(
        python_version=".".join(map(str, sys.version_info[:3])),
        python_supported=python_supported,
        docker_cli=docker_path is not None,
        docker_daemon=docker_daemon,
        docker_version=docker_version,
        openai_package=importlib.util.find_spec("openai") is not None,
        openai_api_key=bool(os.getenv("OPENAI_API_KEY")),
        github_token=bool(os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")),
    )
