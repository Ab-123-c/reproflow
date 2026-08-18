from __future__ import annotations

import subprocess
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath

from reproflow.capsule.schema import ReproSpec

from .models import ExecutionEvidence


class DockerUnavailableError(RuntimeError):
    pass


class DockerSandboxRunner:
    """Run a ReproFlow capsule in an isolated Docker container.

    Setup commands are baked into an ephemeral image. The actual reproduction run
    has networking disabled, a read-only root filesystem, resource limits, no
    host secrets, and no Docker socket mount.
    """

    def __init__(self, docker_bin: str = "docker") -> None:
        self.docker_bin = docker_bin

    def check_available(self) -> None:
        try:
            result = subprocess.run(
                [self.docker_bin, "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise DockerUnavailableError("Docker is not available") from exc
        if result.returncode != 0:
            raise DockerUnavailableError(result.stderr.strip() or "Docker daemon is not available")

    def run(self, spec: ReproSpec) -> ExecutionEvidence:
        return self.run_many(spec, 1)[0]

    def run_many(self, spec: ReproSpec, repetitions: int) -> list[ExecutionEvidence]:
        self.check_available()
        with tempfile.TemporaryDirectory(prefix="reproflow-") as temp:
            root = Path(temp)
            self._write_capsule_files(root, spec.files)
            image = self._build_image(root, spec)
            environment_hash = self._image_hash(image)
            try:
                return [self._run_image(image, spec, environment_hash) for _ in range(repetitions)]
            finally:
                subprocess.run(
                    [self.docker_bin, "image", "rm", "-f", image],
                    capture_output=True,
                    text=True,
                    check=False,
                )

    def _write_capsule_files(self, root: Path, files: dict[str, str]) -> None:
        for relative, content in files.items():
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe capsule file path: {relative}")
            destination = root.joinpath(*path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")

    def _build_image(self, root: Path, spec: ReproSpec) -> str:
        tag = f"reproflow-run-{uuid.uuid4().hex[:12]}"
        lines = [
            f"FROM {spec.environment.image}",
            "WORKDIR /repro",
            "COPY . /repro",
        ]
        for command in spec.setup.commands:
            lines.append(f"RUN {command}")
        (root / "Dockerfile.reproflow").write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = subprocess.run(
            [
                self.docker_bin,
                "build",
                "--pull=false",
                "--tag",
                tag,
                "--file",
                str(root / "Dockerfile.reproflow"),
                str(root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Docker build failed:\n{result.stderr or result.stdout}")
        return tag

    def _image_hash(self, image: str) -> str:
        result = subprocess.run(
            [self.docker_bin, "image", "inspect", "--format", "{{.Id}}", image],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Could not inspect built image: {result.stderr}")
        return result.stdout.strip().removeprefix("sha256:")

    def _run_image(self, image: str, spec: ReproSpec, environment_hash: str) -> ExecutionEvidence:
        command = [
            self.docker_bin,
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "1g",
            "--cpus",
            "1",
            "--pids-limit",
            "128",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--security-opt",
            "no-new-privileges",
            "--cap-drop",
            "ALL",
            image,
            "/bin/sh",
            "-lc",
            spec.run.command,
        ]
        start = time.monotonic()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=spec.run.timeout_seconds,
                check=False,
            )
            timed_out = False
            exit_code: int | None = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = None
            stdout = _to_text(exc.stdout)
            stderr = _to_text(exc.stderr)
        duration_ms = int((time.monotonic() - start) * 1000)

        return ExecutionEvidence(
            command=spec.run.command,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            timed_out=timed_out,
            environment_hash=environment_hash,
        )


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
