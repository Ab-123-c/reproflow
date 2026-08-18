from pydantic import BaseModel


class ExecutionEvidence(BaseModel):
    command: str
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    environment_hash: str
