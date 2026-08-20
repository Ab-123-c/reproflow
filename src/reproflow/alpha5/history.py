from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class RunStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FLAKY = "FLAKY"
    NOT_REPRODUCIBLE = "NOT_REPRODUCIBLE"
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    ERROR = "ERROR"


@dataclass(slots=True)
class RunRecord:
    run_id: str
    issue: str
    status: RunStatus
    attempted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    runs: int = 0
    successful_runs: int = 0
    failure_signature: str | None = None
    score: int | None = None
    environment_hash: str | None = None
    model: str | None = None
    capsule_path: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRecord":
        payload = dict(data)
        payload["status"] = RunStatus(payload["status"])
        return cls(**payload)


class HistoryStore:
    """Small JSON history store with atomic writes.

    Storage format is deliberately boring and inspectable by maintainers.
    """

    def __init__(self, repo: str | Path = ".") -> None:
        self.repo = Path(repo).resolve()
        self.root = self.repo / ".reproflow"
        self.runs_dir = self.root / "runs"
        self.path = self.root / "history.json"

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"History file is invalid JSON: {self.path}") from exc
        if not isinstance(payload, list):
            raise RuntimeError(f"History file must contain a JSON array: {self.path}")
        return payload

    def list(self, limit: int | None = None) -> list[RunRecord]:
        records = [RunRecord.from_dict(item) for item in self._read()]
        records.sort(key=lambda item: item.attempted_at, reverse=True)
        return records if limit is None else records[: max(limit, 0)]

    def get(self, run_id: str) -> RunRecord | None:
        return next((record for record in self.list() if record.run_id == run_id), None)

    def next_run_id(self) -> str:
        numeric_ids: list[int] = []
        for record in self.list():
            try:
                numeric_ids.append(int(record.run_id))
            except ValueError:
                continue
        return f"{(max(numeric_ids, default=0) + 1):03d}"

    def append(self, record: RunRecord, artifacts: dict[str, str] | None = None) -> RunRecord:
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        rows = self._read()
        if any(row.get("run_id") == record.run_id for row in rows):
            raise ValueError(f"Run id already exists: {record.run_id}")
        rows.append(record.to_dict())
        self._atomic_json_write(rows)

        if artifacts:
            run_dir = self.runs_dir / record.run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            for name, content in artifacts.items():
                safe_name = Path(name).name
                (run_dir / safe_name).write_text(content, encoding="utf-8")
        return record

    def _atomic_json_write(self, payload: Any) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix="history-", suffix=".json", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            os.replace(tmp_name, self.path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
