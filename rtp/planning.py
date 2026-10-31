"""Planning: ranking, waves and owner workload.

Ranking is strict and deterministic:

1. priority score, highest first;
2. residual score, highest first (tie-break);
3. effort, lowest first (tie-break);
4. risk id, A..Z (final tie-break).

Waves are filled in rank order with a cumulative **effort budget**. When the
next item would push the running total over the budget, the wave closes and
the item opens the next wave. Wave 3 takes everything left, so nothing is
dropped. Waves run back to back; each wave lasts as long as its slowest
control (``time_to_implement_weeks``).
"""
from __future__ import annotations

from datetime import date, timedelta

from .models import BANDS, OwnerLoad, Plan, PlanItem, Treatment, UNPLANNED_OPTIONS, Wave
from .scoring import DEFAULT_QUICK_WIN_EFFORT, DEFAULT_QUICK_WIN_SCORE, band, score_risk

DEFAULT_WAVE_BUDGET = 12
DEFAULT_WAVE_COUNT = 3
DEFAULT_START_DATE = date(2026, 1, 5)  # a Monday; fixed so output is reproducible

_BAND_RANK = {name: i for i, (name, _, _) in enumerate(BANDS)}


def rank_items(items: list[PlanItem]) -> list[PlanItem]:
    """Sort a copy of ``items`` by the ranking rules and number them 1..n."""
    ordered = sorted(
        items,
        key=lambda i: (-i.priority_score, -i.risk.residual_score, i.effort, i.risk.id),
    )
    for n, item in enumerate(ordered, start=1):
        item.rank = n
    return ordered


def assign_waves(
    ranked: list[PlanItem],
    *,
    wave_budget: int = DEFAULT_WAVE_BUDGET,
    wave_count: int = DEFAULT_WAVE_COUNT,
    start_date: date = DEFAULT_START_DATE,
) -> list[Wave]:
    """Place planned items into waves by cumulative effort budget.

    ``ranked`` must already be in rank order. Items whose treatment option is in
    ``UNPLANNED_OPTIONS`` (Accept) keep ``wave=None``.
    """
    if wave_budget < 1:
        raise ValueError("wave budget must be >= 1")
    if wave_count < 1:
        raise ValueError("wave count must be >= 1")

    waves = [Wave(number=n) for n in range(1, wave_count + 1)]
    current = 0
    running = 0
    for item in ranked:
        if item.risk.treatment_option in UNPLANNED_OPTIONS:
            item.wave = None
            continue
        is_last = current == wave_count - 1
        if not is_last and running > 0 and running + item.effort > wave_budget:
            current += 1
            running = 0
        waves[current].items.append(item)
        item.wave = current + 1
        running += item.effort

    cursor = start_date
    for wave in waves:
        if not wave.items:
            continue
        wave.start = cursor
        wave.end = cursor + timedelta(weeks=wave.weeks)
        for item in wave.items:
            item.wave_start = wave.start
            item.wave_end = wave.start + timedelta(weeks=item.weeks)
        cursor = wave.end
    return waves


def owner_workload(items: list[PlanItem]) -> list[OwnerLoad]:
    """One line per owner, sorted by planned effort (desc) then name."""
    by_owner: dict[str, list[PlanItem]] = {}
    for item in items:
        by_owner.setdefault(item.risk.owner, []).append(item)
    loads = []
    for owner, group in by_owner.items():
        planned = [i for i in group if i.planned]
        highest = max(group, key=lambda i: _BAND_RANK[band(i.risk.residual_score)])
        loads.append(
            OwnerLoad(
                owner=owner,
                risks=len(group),
                planned=len(planned),
                effort=sum(i.effort for i in planned),
                wave1=sum(1 for i in planned if i.wave == 1),
                quick_wins=sum(1 for i in group if i.quick_win),
                highest_band=band(highest.risk.residual_score),
            )
        )
    loads.sort(key=lambda o: (-o.effort, -o.risks, o.owner))
    return loads


def build_plan(
    risks: list,
    catalogue: dict[str, Treatment],
    *,
    title: str = "Risk treatment plan",
    start_date: date = DEFAULT_START_DATE,
    wave_budget: int = DEFAULT_WAVE_BUDGET,
    wave_count: int = DEFAULT_WAVE_COUNT,
    quick_win_score: int = DEFAULT_QUICK_WIN_SCORE,
    quick_win_effort: int = DEFAULT_QUICK_WIN_EFFORT,
    warnings: list[str] | None = None,
) -> Plan:
    """Score, rank and schedule every risk. Pure function of its inputs."""
    items = [
        score_risk(r, catalogue, quick_win_score=quick_win_score, quick_win_effort=quick_win_effort)
        for r in risks
    ]
    ranked = rank_items(items)
    waves = assign_waves(ranked, wave_budget=wave_budget, wave_count=wave_count, start_date=start_date)
    notes = list(warnings or [])
    for item in ranked:
        for name in item.controls_missing:
            notes.append(
                f"{item.risk.id}: planned control {name!r} is not in the treatment catalogue — "
                "default effort/cost applied"
            )
    return Plan(
        title=title,
        start_date=start_date,
        wave_budget=wave_budget,
        quick_win_score=quick_win_score,
        quick_win_effort=quick_win_effort,
        items=ranked,
        waves=waves,
        owners=owner_workload(ranked),
        warnings=notes,
    )
