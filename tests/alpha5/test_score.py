from reproflow.alpha5.score import ScoreInput, calculate_repro_score


def test_perfect_score() -> None:
    score = calculate_repro_score(
        ScoreInput(
            total_runs=3,
            matching_failures=3,
            source_size=100,
            minimized_size=1,
            has_environment_fingerprint=True,
            has_environment_lock=True,
            has_stable_failure_signature=True,
            has_portable_runner=True,
        )
    )
    assert score.total >= 99
    assert score.repeatability == 30
    assert score.failure_precision == 20


def test_invalid_counts() -> None:
    try:
        calculate_repro_score(ScoreInput(total_runs=1, matching_failures=2))
    except ValueError:
        return
    raise AssertionError("Expected ValueError")
