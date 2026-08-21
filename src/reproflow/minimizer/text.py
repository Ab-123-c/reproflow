from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class MinimizationResult:
    original: str
    minimized: str
    checks: int
    accepted_reductions: int
    exhausted_budget: bool

    @property
    def removed_chars(self) -> int:
        return len(self.original) - len(self.minimized)

    @property
    def reduction_ratio(self) -> float:
        if not self.original:
            return 0.0
        return self.removed_chars / len(self.original)


def minimize_text(
    text: str,
    still_reproduces: Callable[[str], bool],
    *,
    max_checks: int = 60,
    min_length: int = 1,
) -> MinimizationResult:
    """Minimize text with a bounded ddmin-style deletion loop.

    ``still_reproduces`` is the only oracle. ReproFlow's CLI wires this callback to
    the deterministic Verifier, so a reduction is accepted only when the target
    failure continues to reproduce.
    """
    if max_checks < 1:
        raise ValueError("max_checks must be at least 1")
    if min_length < 0:
        raise ValueError("min_length cannot be negative")
    if min_length > len(text):
        raise ValueError("min_length cannot exceed input length")

    current = text
    checks = 0
    accepted = 0
    granularity = 2

    while len(current) > min_length and checks < max_checks:
        chunk_size = max(1, (len(current) + granularity - 1) // granularity)
        reduced = False

        for start in range(0, len(current), chunk_size):
            if checks >= max_checks:
                break
            end = min(len(current), start + chunk_size)
            candidate = current[:start] + current[end:]
            if len(candidate) < min_length or candidate == current:
                continue

            checks += 1
            if still_reproduces(candidate):
                current = candidate
                accepted += 1
                granularity = max(2, granularity - 1)
                reduced = True
                break

        if reduced:
            continue
        if granularity >= len(current):
            break
        granularity = min(len(current), granularity * 2)

    return MinimizationResult(
        original=text,
        minimized=current,
        checks=checks,
        accepted_reductions=accepted,
        exhausted_budget=checks >= max_checks,
    )
