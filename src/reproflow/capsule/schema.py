from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceMetadata(StrictModel):
    type: str
    issue: int | str | None = None
    url: str | None = None


class Metadata(StrictModel):
    id: str
    title: str
    source: SourceMetadata | None = None

    @field_validator("id", "title")
    @classmethod
    def non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("metadata id and title cannot be empty")
        if any(ord(char) < 32 for char in value):
            raise ValueError("metadata id and title cannot contain control characters")
        if len(value) > 200:
            raise ValueError("metadata id and title must be at most 200 characters")
        return value

    @field_validator("id")
    @classmethod
    def safe_identifier(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError("metadata id cannot contain path separators")
        return value


class Environment(StrictModel):
    image: str = "python:3.12-slim"
    variables: dict[str, str] = Field(default_factory=dict)

    @field_validator("image")
    @classmethod
    def safe_image_reference(cls, value: str) -> str:
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("image must be a single Docker image reference without whitespace")
        return value

    @field_validator("variables")
    @classmethod
    def safe_environment_variables(cls, value: dict[str, str]) -> dict[str, str]:
        key_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
        for key, variable in value.items():
            if not key_pattern.fullmatch(key):
                raise ValueError(f"invalid environment variable name: {key!r}")
            if "\x00" in variable:
                raise ValueError(f"environment variable {key!r} contains a NUL byte")
            if len(variable) > 32_768:
                raise ValueError(f"environment variable {key!r} is too large")
        return value


class Setup(StrictModel):
    commands: list[str] = Field(default_factory=list)

    @field_validator("commands")
    @classmethod
    def non_empty_commands(cls, value: list[str]) -> list[str]:
        if any(not command.strip() for command in value):
            raise ValueError("setup commands cannot be empty")
        if any("\x00" in command for command in value):
            raise ValueError("setup commands cannot contain NUL bytes")
        if any(len(command) > 4_000 for command in value):
            raise ValueError("setup commands must be at most 4000 characters")
        return value


class RunSpec(StrictModel):
    command: str
    timeout_seconds: int = Field(default=30, ge=1, le=600)

    @field_validator("command")
    @classmethod
    def non_empty_command(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("run command cannot be empty")
        if "\x00" in value:
            raise ValueError("run command cannot contain a NUL byte")
        if len(value) > 10_000:
            raise ValueError("run command must be at most 10000 characters")
        return value


class FailureExpectation(StrictModel):
    type: Literal["exception", "crash", "nonzero_exit", "timeout", "output_mismatch"]
    exit_code: int | None = None
    exception_class: str | None = None
    signal: int | None = Field(default=None, ge=1, le=64)
    stdout_contains: list[str] = Field(default_factory=list)
    stderr_contains: list[str] = Field(default_factory=list)
    stdout_equals: str | None = None
    stderr_equals: str | None = None
    stdout_not_contains: list[str] = Field(default_factory=list)
    stderr_not_contains: list[str] = Field(default_factory=list)

    @field_validator("exception_class")
    @classmethod
    def valid_exception_class(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", value):
            raise ValueError("exception_class must be a Python-style class name")
        return value

    @model_validator(mode="after")
    def require_target_specific_failure(self) -> "FailureExpectation":
        for name, values in (
            ("stdout_contains", self.stdout_contains),
            ("stderr_contains", self.stderr_contains),
            ("stdout_not_contains", self.stdout_not_contains),
            ("stderr_not_contains", self.stderr_not_contains),
        ):
            if any(not value for value in values):
                raise ValueError(f"{name} entries cannot be empty")

        if self.exception_class is not None and self.type != "exception":
            raise ValueError("exception_class is only valid for exception failures")
        if self.signal is not None and self.type != "crash":
            raise ValueError("signal is only valid for crash failures")

        output_fields_present = (
            self.stdout_equals is not None
            or self.stderr_equals is not None
            or bool(self.stdout_not_contains)
            or bool(self.stderr_not_contains)
        )
        if output_fields_present and self.type != "output_mismatch":
            raise ValueError(
                "stdout_equals, stderr_equals, stdout_not_contains, and stderr_not_contains "
                "are only valid for output_mismatch failures"
            )
        if self.type == "output_mismatch" and not output_fields_present:
            raise ValueError(
                "output_mismatch failures require stdout_equals, stderr_equals, "
                "stdout_not_contains, or stderr_not_contains"
            )
        if self.type == "output_mismatch" and (self.stdout_contains or self.stderr_contains):
            raise ValueError(
                "output_mismatch uses equality or forbidden-output constraints; "
                "stdout_contains/stderr_contains describe matching output"
            )
        if self.type == "output_mismatch" and self.exit_code not in (None, 0):
            raise ValueError("output_mismatch requires exit_code 0 when exit_code is specified")

        if self.type == "exception" and not (self.exception_class or self.stderr_contains):
            raise ValueError(
                "exception failures require exception_class or stderr_contains so unrelated "
                "non-zero exits cannot be mistaken for the target bug"
            )
        if self.type == "crash" and not (
            self.signal is not None
            or self.exit_code is not None
            or self.stdout_contains
            or self.stderr_contains
        ):
            raise ValueError(
                "crash failures require signal, exit_code, stdout_contains, or stderr_contains"
            )
        return self


class VerificationPolicy(StrictModel):
    repetitions: int = Field(default=3, ge=1, le=20)
    required_failures: int = Field(default=3, ge=1, le=20)

    @model_validator(mode="after")
    def required_not_greater_than_repetitions(self) -> "VerificationPolicy":
        if self.required_failures > self.repetitions:
            raise ValueError("required_failures cannot exceed repetitions")
        return self


class ReproSpec(StrictModel):
    schema_: Literal["reproflow/v1"] = Field(alias="schema")
    metadata: Metadata
    environment: Environment = Field(default_factory=Environment)
    setup: Setup = Field(default_factory=Setup)
    files: dict[str, str] = Field(default_factory=dict)
    run: RunSpec
    failure: FailureExpectation
    verification: VerificationPolicy = Field(default_factory=VerificationPolicy)

    @field_validator("files")
    @classmethod
    def safe_file_paths(cls, value: dict[str, str]) -> dict[str, str]:
        for relative in value:
            path = PurePosixPath(relative)
            if (
                not relative.strip()
                or not path.parts
                or relative.endswith("/")
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in relative
                or "\x00" in relative
            ):
                raise ValueError(f"unsafe capsule file path: {relative!r}")
            if len(relative) > 240:
                raise ValueError(f"capsule file path is too long: {relative!r}")
        return value
