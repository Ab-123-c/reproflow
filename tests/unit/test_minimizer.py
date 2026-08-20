import pytest

from reproflow.minimizer import minimize_text


def test_minimizer_keeps_only_failure_trigger() -> None:
    result = minimize_text(
        "prefix-123-TRIGGER-xyz-suffix",
        lambda candidate: "TRIGGER" in candidate,
        max_checks=100,
    )

    assert "TRIGGER" in result.minimized
    assert len(result.minimized) < len(result.original)
    assert result.checks <= 100
    assert result.accepted_reductions > 0


def test_minimizer_respects_budget() -> None:
    result = minimize_text("abcdefgh", lambda _: False, max_checks=1)
    assert result.minimized == "abcdefgh"
    assert result.checks == 1
    assert result.exhausted_budget is True


@pytest.mark.parametrize("kwargs", [{"max_checks": 0}, {"min_length": -1}, {"min_length": 4}])
def test_minimizer_rejects_invalid_bounds(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        minimize_text("abc", lambda _: True, **kwargs)
