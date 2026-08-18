from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BugReport(BaseModel):
    """Structured facts extracted from an untrusted bug report."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    reproduction_steps: list[str] = Field(default_factory=list)
    environment: dict[str, str] = Field(default_factory=dict)
    error_messages: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
