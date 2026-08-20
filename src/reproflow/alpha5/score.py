from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ScoreInput:
    total_runs: int
    matching_failures: int
    source_size: int | None = None
    minimized_size: int | None = None
    has_environment_fingerprint: bool = False
    has_environment_lock: bool = False
    has_stable_failure_signature: bool = False
    has_portable_runner: bool = False


@dataclass(frozen=True, slots=True)
class ReproScore:
    repeatability: int
    minimality: int
    environment_lock: int
    failure_precision: int
    portability: int
    total: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def calculate_repro_score(data: ScoreInput) -> ReproScore:
    if data.total_runs < 0 or data.matching_failures < 0:
        raise ValueError("Run counts cannot be negative")
    if data.matching_failures > data.total_runs:
        raise ValueError("matching_failures cannot exceed total_runs")

    repeatability_ratio = 0.0 if data.total_runs == 0 else data.matching_failures / data.total_runs
    repeatability = round(30 * repeatability_ratio)

    if data.source_size and data.source_size > 0 and data.minimized_size is not None:
        reduction = 1 - (data.minimized_size / data.source_size)
        # A valid minimized result gets a useful floor; stronger reduction gets the rest.
        minimality = round(8 + 12 * _clamp(reduction))
    else:
        minimality = 0

    environment_lock = 0
    if data.has_environment_fingerprint:
        environment_lock += 10
    if data.has_environment_lock:
        environment_lock += 10

    failure_precision = 20 if data.has_stable_failure_signature else 0
    portability = 10 if data.has_portable_runner else 0
    total = repeatability + minimality + environment_lock + failure_precision + portability

    return ReproScore(
        repeatability=repeatability,
        minimality=minimality,
        environment_lock=environment_lock,
        failure_precision=failure_precision,
        portability=portability,
        total=total,
    )
