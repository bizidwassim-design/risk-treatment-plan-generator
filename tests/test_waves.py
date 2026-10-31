from __future__ import annotations

from datetime import date, timedelta

from conftest import make_catalogue, make_risk

from rtp.planning import assign_waves, build_plan, owner_workload, rank_items
from rtp.scoring import score_risk


def _items(cat, *risks):
    return [score_risk(r, cat) for r in risks]


def test_rank_orders_by_priority_then_residual_then_effort_then_id() -> None:
    cat = make_catalogue(("Cheap", 1, "Low", 1), ("Mid", 2, "Low", 2), ("Dear", 4, "High", 8))
    items = _items(
        cat,
        make_risk("R-03", residual_likelihood=2, residual_impact=5, controls=("Mid",)),  # 10/2 = 5.0
        make_risk("R-01", residual_likelihood=4, residual_impact=5, controls=("Dear",)),  # 20/4 = 5.0
        make_risk("R-02", residual_likelihood=5, residual_impact=1, controls=("Cheap",)),  # 5/1 = 5.0
        make_risk("R-04", residual_likelihood=5, residual_impact=5, controls=("Cheap",)),  # 25
    )
    ranked = rank_items(items)
    assert [i.risk.id for i in ranked] == ["R-04", "R-01", "R-03", "R-02"]
    assert [i.rank for i in ranked] == [1, 2, 3, 4]


def test_waves_fill_by_cumulative_effort_budget() -> None:
    cat = make_catalogue(("E1", 1, "Low", 1), ("E3", 3, "Low", 3), ("E5", 5, "High", 5))
    items = _items(
        cat,
        make_risk("R-1", residual_likelihood=5, residual_impact=5, controls=("E1",)),  # 25
        make_risk("R-2", residual_likelihood=4, residual_impact=5, controls=("E3",)),  # 6.67
        make_risk("R-3", residual_likelihood=3, residual_impact=5, controls=("E3",)),  # 5
        make_risk("R-4", residual_likelihood=2, residual_impact=5, controls=("E5",)),  # 2
        make_risk("R-5", residual_likelihood=1, residual_impact=5, controls=("E5",)),  # 1
    )
    waves = assign_waves(rank_items(items), wave_budget=6, start_date=date(2026, 1, 5))
    assert [[i.risk.id for i in w.items] for w in waves] == [["R-1", "R-2"], ["R-3"], ["R-4", "R-5"]]
    assert [w.effort for w in waves] == [4, 3, 10]  # last wave takes the rest, beyond the budget


def test_first_item_always_fits_even_if_bigger_than_budget() -> None:
    cat = make_catalogue(("Huge", 5, "High", 20))
    items = _items(cat, make_risk("R-1", controls=("Huge",)))
    waves = assign_waves(rank_items(items), wave_budget=2)
    assert waves[0].items[0].risk.id == "R-1" and waves[0].items[0].wave == 1


def test_accepted_risks_are_not_planned() -> None:
    cat = make_catalogue(("X", 1, "Low", 1))
    items = _items(cat, make_risk("R-1", option="Accept", controls=()), make_risk("R-2", controls=("X",)))
    waves = assign_waves(rank_items(items))
    ids = [i.risk.id for w in waves for i in w.items]
    assert ids == ["R-2"]
    accepted = next(i for i in items if i.risk.id == "R-1")
    assert accepted.wave is None and accepted.wave_start is None and not accepted.planned


def test_waves_run_back_to_back_and_last_as_long_as_slowest_control() -> None:
    cat = make_catalogue(("Fast", 1, "Low", 2), ("Slow", 1, "Low", 7))
    items = _items(
        cat,
        make_risk("R-1", residual_likelihood=5, residual_impact=5, controls=("Slow",)),
        make_risk("R-2", residual_likelihood=4, residual_impact=5, controls=("Fast",)),
        make_risk("R-3", residual_likelihood=3, residual_impact=5, controls=("Fast",)),
    )
    start = date(2026, 1, 5)
    waves = assign_waves(rank_items(items), wave_budget=2, start_date=start)
    assert waves[0].start == start
    assert waves[0].end == start + timedelta(weeks=7)
    assert waves[1].start == waves[0].end
    assert waves[1].end == waves[1].start + timedelta(weeks=2)
    assert waves[2].items == [] and waves[2].start is None
    r2 = waves[0].items[1]
    assert r2.wave_end == start + timedelta(weeks=2)  # item end uses its own duration


def test_single_wave_takes_everything() -> None:
    cat = make_catalogue(("X", 5, "High", 1))
    items = _items(cat, *(make_risk(f"R-{n}", controls=("X",)) for n in range(4)))
    waves = assign_waves(rank_items(items), wave_budget=1, wave_count=1)
    assert len(waves) == 1 and len(waves[0].items) == 4


def test_owner_workload_counts() -> None:
    cat = make_catalogue(("Cheap", 1, "Low", 1), ("Dear", 4, "High", 8))
    plan = build_plan(
        [
            make_risk("R-1", owner="Alice", residual_likelihood=4, residual_impact=4, controls=("Cheap",)),
            make_risk("R-2", owner="Alice", residual_likelihood=2, residual_impact=2, controls=("Dear",)),
            make_risk("R-3", owner="Bob", residual_likelihood=5, residual_impact=5, controls=("Dear",)),
            make_risk("R-4", owner="Bob", option="Accept", controls=()),
        ],
        cat,
        wave_budget=5,
    )
    loads = {o.owner: o for o in owner_workload(plan.items)}
    assert loads["Alice"].risks == 2 and loads["Alice"].effort == 5 and loads["Alice"].quick_wins == 1
    assert loads["Alice"].highest_band == "High"
    assert loads["Bob"].risks == 2 and loads["Bob"].planned == 1 and loads["Bob"].effort == 4
    assert loads["Bob"].highest_band == "Critical"
    assert [o.owner for o in plan.owners] == ["Alice", "Bob"]  # sorted by planned effort desc


def test_missing_catalogue_entry_becomes_a_warning() -> None:
    plan = build_plan([make_risk("R-1", controls=("Not there",))], {})
    assert any("Not there" in w for w in plan.warnings)
    assert plan.items[0].effort == 3
