from __future__ import annotations

from conftest import make_catalogue, make_risk

from rtp.planning import build_plan
from rtp.reader import read_register, read_treatments


def test_quick_wins_need_high_residual_and_low_effort() -> None:
    cat = make_catalogue(("Cheap", 1, "Low", 1), ("Small", 2, "Low", 2), ("Project", 3, "Medium", 6))
    plan = build_plan(
        [
            make_risk("R-1", residual_likelihood=3, residual_impact=4, controls=("Cheap",)),  # 12, effort 1 -> yes
            make_risk("R-2", residual_likelihood=5, residual_impact=2, controls=("Small",)),  # 10, effort 2 -> yes
            make_risk("R-3", residual_likelihood=3, residual_impact=3, controls=("Cheap",)),  # 9 -> no
            make_risk("R-4", residual_likelihood=5, residual_impact=5, controls=("Project",)),  # effort 3 -> no
        ],
        cat,
    )
    assert sorted(i.risk.id for i in plan.quick_wins) == ["R-1", "R-2"]


def test_quick_win_thresholds_are_configurable() -> None:
    cat = make_catalogue(("Project", 3, "Medium", 6))
    risks = [make_risk("R-1", residual_likelihood=3, residual_impact=3, controls=("Project",))]
    assert build_plan(risks, cat).quick_wins == []
    assert len(build_plan(risks, cat, quick_win_score=9, quick_win_effort=3).quick_wins) == 1


def test_quick_wins_float_to_the_top_of_wave_one() -> None:
    cat = make_catalogue(("Cheap", 1, "Low", 1), ("Programme", 5, "High", 20))
    plan = build_plan(
        [
            make_risk("R-A", residual_likelihood=5, residual_impact=5, controls=("Programme",)),  # 25/5 = 5
            make_risk("R-B", residual_likelihood=2, residual_impact=5, controls=("Cheap",)),  # 10/1 = 10
        ],
        cat,
    )
    assert plan.items[0].risk.id == "R-B" and plan.items[0].quick_win
    assert plan.items[0].wave == 1


def test_example_register_quick_wins(example_paths) -> None:
    register, treatments = example_paths
    risks, warnings = read_register(register)
    plan = build_plan(risks, read_treatments(treatments), warnings=warnings)
    assert [i.risk.id for i in plan.quick_wins] == ["R-02", "R-03"]
    # R-13 ranks third on priority but its residual is Medium, so it is not a quick win
    r13 = next(i for i in plan.items if i.risk.id == "R-13")
    assert r13.rank == 3 and not r13.quick_win
