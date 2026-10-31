from __future__ import annotations

import pytest
from conftest import make_catalogue, make_risk

from rtp.scoring import band, exposure_weight, is_quick_win, priority_score, resolve_effort, score_risk


@pytest.mark.parametrize(
    "score,expected",
    [(1, "Low"), (4, "Low"), (5, "Medium"), (9, "Medium"), (10, "High"), (16, "High"), (17, "Critical"), (25, "Critical")],
)
def test_band_boundaries(score: int, expected: str) -> None:
    assert band(score) == expected


@pytest.mark.parametrize("score", [0, 26, -3])
def test_band_rejects_out_of_range(score: int) -> None:
    with pytest.raises(ValueError):
        band(score)


def test_exposure_weights_are_case_insensitive() -> None:
    assert exposure_weight("Internet") == 1.5
    assert exposure_weight("partner") == 1.25
    assert exposure_weight("INTERNAL") == 1.0
    assert exposure_weight("isolated") == 0.75
    with pytest.raises(ValueError):
        exposure_weight("dmz")


def test_priority_formula() -> None:
    # residual 12 x internet 1.5 / effort 1
    assert priority_score(12, 1.5, 1) == 18.0
    # residual 15 x internal 1.0 / effort 3
    assert priority_score(15, 1.0, 3) == 5.0
    # rounding to two decimals keeps CSV stable
    assert priority_score(8, 1.25, 3) == 3.33
    with pytest.raises(ValueError):
        priority_score(10, 1.0, 0)


def test_quick_win_rule() -> None:
    assert is_quick_win(10, 2)
    assert is_quick_win(25, 1)
    assert not is_quick_win(9, 1)  # Medium residual is not a quick win, however cheap
    assert not is_quick_win(20, 3)  # too much effort
    assert is_quick_win(9, 3, quick_win_score=9, quick_win_effort=3)


def test_resolve_effort_single_control() -> None:
    cat = make_catalogue(("Control X", 2, "Low", 4))
    effort, cost, weeks, found, missing = resolve_effort(make_risk(controls=("control x",)), cat)
    assert (effort, cost, weeks) == (2, "Low", 4)
    assert found == ("Control X",) and missing == ()


def test_resolve_effort_bundle_sums_effort_and_takes_max_weeks_and_highest_cost() -> None:
    cat = make_catalogue(("A", 2, "Low", 3), ("B", 1, "High", 8))
    effort, cost, weeks, found, missing = resolve_effort(make_risk(controls=("A", "B")), cat)
    assert (effort, cost, weeks) == (3, "High", 8)
    assert found == ("A", "B")


def test_resolve_effort_bundle_is_capped_at_five() -> None:
    cat = make_catalogue(("A", 4, "Medium", 3), ("B", 4, "Medium", 3))
    effort, *_ = resolve_effort(make_risk(controls=("A", "B")), cat)
    assert effort == 5


def test_resolve_effort_defaults_when_control_unknown() -> None:
    effort, cost, weeks, found, missing = resolve_effort(make_risk(controls=("Nope",)), {})
    assert (effort, cost, weeks) == (3, "Unknown", 6)
    assert found == () and missing == ("Nope",)


def test_score_risk_builds_item() -> None:
    cat = make_catalogue(("Control X", 1, "Low", 1))
    item = score_risk(make_risk(exposure="internet", residual_likelihood=3, residual_impact=4), cat)
    assert item.risk.residual_score == 12
    assert item.exposure_weight == 1.5
    assert item.priority_score == 18.0
    assert item.quick_win is True
    assert item.wave is None and item.rank == 0
