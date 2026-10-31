"""Scoring: rating bands, exposure weight, priority score and quick-win detection.

    priority = residual score x exposure weight x (1 / effort)

* residual score  = residual likelihood x residual impact (1..25)
* exposure weight = internet 1.5 · partner 1.25 · internal 1.0 · isolated 0.75
* effort          = 1 (trivial) .. 5 (programme), from treatments.csv

A quick win is a risk whose residual score is at least ``quick_win_score``
(default 10 = High or Critical) and whose effort is at most
``quick_win_effort`` (default 2).
"""
from __future__ import annotations

from .models import (
    BANDS,
    COST_BANDS,
    DEFAULT_COST_BAND,
    DEFAULT_EFFORT,
    DEFAULT_WEEKS,
    EXPOSURE_WEIGHTS,
    PlanItem,
    Risk,
    Treatment,
)

DEFAULT_QUICK_WIN_SCORE = 10
DEFAULT_QUICK_WIN_EFFORT = 2


def band(score: int) -> str:
    """Return the rating band for a 1..25 score."""
    for name, low, high in BANDS:
        if low <= score <= high:
            return name
    raise ValueError(f"score {score} is outside 1..25")


def exposure_weight(exposure: str) -> float:
    try:
        return EXPOSURE_WEIGHTS[exposure.strip().lower()]
    except KeyError:
        known = ", ".join(EXPOSURE_WEIGHTS)
        raise ValueError(f"unknown exposure {exposure!r}; expected one of: {known}") from None


def priority_score(residual_score: int, weight: float, effort: int) -> float:
    """``residual x weight / effort``, rounded to two decimals so that CSV and
    Markdown stay stable across platforms."""
    if effort < 1:
        raise ValueError("effort must be >= 1")
    return round(residual_score * weight / effort, 2)


def is_quick_win(
    residual_score: int,
    effort: int,
    *,
    quick_win_score: int = DEFAULT_QUICK_WIN_SCORE,
    quick_win_effort: int = DEFAULT_QUICK_WIN_EFFORT,
) -> bool:
    return residual_score >= quick_win_score and effort <= quick_win_effort


def resolve_effort(
    risk: Risk, catalogue: dict[str, Treatment]
) -> tuple[int, str, int, tuple[str, ...], tuple[str, ...]]:
    """Look the risk's planned controls up in the catalogue.

    Returns ``(effort, cost_band, weeks, found, missing)``.

    * several controls: effort is the **sum**, weeks the **maximum**, cost band
      the **highest** band among them;
    * no planned control, or none found: defaults (effort 3, 6 weeks, "Unknown").
    """
    found: list[str] = []
    missing: list[str] = []
    treatments: list[Treatment] = []
    for name in risk.planned_controls:
        key = name.strip().lower()
        if key in catalogue:
            found.append(catalogue[key].control)
            treatments.append(catalogue[key])
        else:
            missing.append(name)
    if not treatments:
        return DEFAULT_EFFORT, DEFAULT_COST_BAND, DEFAULT_WEEKS, tuple(found), tuple(missing)

    # Effort stays on the 1..5 scale; a bundle of two "3"s is already a programme.
    effort = min(sum(t.effort for t in treatments), 5)
    weeks = max(t.time_to_implement_weeks for t in treatments)
    order = {b.lower(): i for i, b in enumerate(COST_BANDS)}
    cost = max((t.cost_band for t in treatments), key=lambda b: order.get(b.lower(), -1))
    return effort, cost, weeks, tuple(found), tuple(missing)


def score_risk(
    risk: Risk,
    catalogue: dict[str, Treatment],
    *,
    quick_win_score: int = DEFAULT_QUICK_WIN_SCORE,
    quick_win_effort: int = DEFAULT_QUICK_WIN_EFFORT,
) -> PlanItem:
    """Build the unplanned ``PlanItem`` (no rank, no wave yet) for one risk."""
    effort, cost, weeks, found, missing = resolve_effort(risk, catalogue)
    weight = exposure_weight(risk.exposure)
    score = priority_score(risk.residual_score, weight, effort)
    quick = is_quick_win(
        risk.residual_score,
        effort,
        quick_win_score=quick_win_score,
        quick_win_effort=quick_win_effort,
    )
    return PlanItem(
        risk=risk,
        effort=effort,
        cost_band=cost,
        weeks=weeks,
        exposure_weight=weight,
        priority_score=score,
        quick_win=quick,
        controls_found=found,
        controls_missing=missing,
    )
