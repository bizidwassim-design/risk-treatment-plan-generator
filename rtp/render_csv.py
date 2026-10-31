"""plan.csv — one row per risk, in rank order, LF line endings."""
from __future__ import annotations

import csv
from pathlib import Path

from .models import Plan, PlanItem
from .scoring import band

COLUMNS: tuple[str, ...] = (
    "rank",
    "id",
    "title",
    "asset",
    "owner",
    "treatment_option",
    "exposure",
    "exposure_weight",
    "inherent_score",
    "inherent_band",
    "residual_score",
    "residual_band",
    "planned_control",
    "effort",
    "cost_band",
    "time_to_implement_weeks",
    "priority_score",
    "quick_win",
    "wave",
    "wave_start",
    "wave_end",
)


def item_row(item: PlanItem) -> dict[str, str]:
    r = item.risk
    return {
        "rank": str(item.rank),
        "id": r.id,
        "title": r.title,
        "asset": r.asset,
        "owner": r.owner,
        "treatment_option": r.treatment_option,
        "exposure": r.exposure,
        "exposure_weight": f"{item.exposure_weight:g}",
        "inherent_score": str(r.inherent_score),
        "inherent_band": band(r.inherent_score),
        "residual_score": str(r.residual_score),
        "residual_band": band(r.residual_score),
        "planned_control": "; ".join(r.planned_controls),
        "effort": str(item.effort),
        "cost_band": item.cost_band,
        "time_to_implement_weeks": str(item.weeks),
        "priority_score": f"{item.priority_score:.2f}",
        "quick_win": "yes" if item.quick_win else "no",
        "wave": str(item.wave) if item.wave else "",
        "wave_start": item.wave_start.isoformat() if item.wave_start else "",
        "wave_end": item.wave_end.isoformat() if item.wave_end else "",
    }


def render_csv(plan: Plan, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for item in plan.items:
            writer.writerow(item_row(item))
