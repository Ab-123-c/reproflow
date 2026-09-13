"""ReproFlow Alpha 5 utilities.

This package is intentionally self-contained so it can be dropped into an
existing ReproFlow checkout without replacing Alpha 1-4 modules.
"""

from .environment import EnvironmentFingerprint, build_environment_fingerprint
from .history import HistoryStore, RunRecord, RunStatus
from .regression import RegressionTest, generate_regression_test
from .score import ReproScore, ScoreInput, calculate_repro_score

__all__ = [
    "EnvironmentFingerprint",
    "HistoryStore",
    "RegressionTest",
    "ReproScore",
    "RunRecord",
    "RunStatus",
    "ScoreInput",
    "build_environment_fingerprint",
    "calculate_repro_score",
    "generate_regression_test",
]

ALPHA_VERSION = "0.1.0-alpha.5"
