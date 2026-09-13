from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path, PurePosixPath

from reproflow.capsule.schema import ReproSpec

from .models import ExecutionEvidence


class DockerUnavailableError(RuntimeError):
    pass


MAX_CAPTURE_CHARS = 1_000_000


class DockerSandboxRunner:
    """Run a ReproFlow capsule in an isolated Docker container.

    Setup commands are baked into an ephemeral image. The actual reproduction run
    has networking disabled, a read-only root filesystem, resource limits, no
    host secrets, and no Docker socket mount.
    """

    def __init__(self, docker_bin: str = "docker", source_root: Path | None = None) -> None:
        self.docker_bin = docker_bin
        self.source_root = source_root.resolve() if source_root is not None else None

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
        if repetitions < 1:
            raise ValueError("repetitions must be at least 1")
        self.check_available()
        with tempfile.TemporaryDirectory(prefix="reproflow-") as temp:
            root = Path(temp)
            if self.source_root is not None:
                self._copy_source_tree(self.source_root, root)
            self._write_capsule_files(root, spec.files)
            image = self._build_image(root, spec)
            environment_hash = _environment_hash(self._image_hash(image), spec)
            try:
                return [self._run_image(image, spec, environment_hash) for _ in range(repetitions)]
            finally:
                subprocess.run(
                    [self.docker_bin, "image", "rm", "-f", image],
                    capture_output=True,
                    text=True,
                    check=False,
                )
    def _copy_source_tree(self, source: Path, destination: Path) -> None:
        if not source.is_dir():
            raise ValueError(f"Source repository does not exist: {source}")
        skip_dirs = {".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".repro", ".reproflow", "node_modules"}
        for path in source.rglob("*"):
            relative = path.relative_to(source)
            if any(part in skip_dirs for part in relative.parts):
                continue
            if path.is_symlink():
                continue
            target = destination / relative
            if path.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            elif path.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)

    def _write_capsule_files(self, root: Path, files: dict[str, str]) -> None:
        for relative, content in files.items():
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe capsule file path: {relative}")
            destination = root.joinpath(*path.parts)
            if self.source_root is not None and destination.exists():
                raise ValueError(f"Capsule file would overwrite source repository content: {relative}")
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
            "--init",
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
        ]
        for key, value in sorted(spec.environment.variables.items()):
            command.extend(["--env", f"{key}={value}"])
        command.extend(
            [
                image,
                "/bin/sh",
                "-lc",
                spec.run.command,
            ]
        )
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
            stdout=_bounded_output(stdout),
            stderr=_bounded_output(stderr),
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


def _bounded_output(value: str, limit: int = MAX_CAPTURE_CHARS) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n... [output truncated by ReproFlow]\n"


def _environment_hash(image_hash: str, spec: ReproSpec) -> str:
    """Identify the effective runtime, including declared process variables."""
    if not spec.environment.variables:
        return image_hash
    payload = json.dumps(spec.environment.variables, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(f"{image_hash}\n{payload}".encode("utf-8")).hexdigest()[:16]
    return f"{image_hash}:{digest}"
