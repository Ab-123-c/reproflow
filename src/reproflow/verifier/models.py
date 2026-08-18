from pydantic import BaseModel, Field

from reproflow.sandbox.models import ExecutionEvidence


class RunVerification(BaseModel):
    matched: bool
    reasons: list[str] = Field(default_factory=list)
    signature: str | None = None
    evidence: ExecutionEvidence


class VerificationResult(BaseModel):
    reproduced: bool
    successful_runs: int
    total_runs: int
    stable_signature: str | None = None
    runs: list[RunVerification] = Field(default_factory=list)
