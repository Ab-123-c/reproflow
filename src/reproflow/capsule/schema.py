from __future__ import annotations

import re
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


class Environment(StrictModel):
    image: str = "python:3.12-slim"

    @field_validator("image")
    @classmethod
    def safe_image_reference(cls, value: str) -> str:
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("image must be a single Docker image reference without whitespace")
        return value


class Setup(StrictModel):
    commands: list[str] = Field(default_factory=list)


class RunSpec(StrictModel):
    command: str
    timeout_seconds: int = Field(default=30, ge=1, le=600)


class FailureExpectation(StrictModel):
    type: Literal["exception", "crash", "nonzero_exit", "timeout", "output_mismatch"]
    exit_code: int | None = None
    exception_class: str | None = None
    signal: int | None = Field(default=None, ge=1, le=64)
    stdout_contains: list[str] = Field(default_factory=list)
    stderr_contains: list[str] = Field(default_factory=list)

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
        if self.exception_class is not None and self.type != "exception":
            raise ValueError("exception_class is only valid for exception failures")
        if self.signal is not None and self.type != "crash":
            raise ValueError("signal is only valid for crash failures")

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
