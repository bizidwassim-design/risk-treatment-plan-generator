from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rtp.models import Risk, Treatment  # noqa: E402

EXAMPLES = ROOT / "examples"


def make_risk(
    rid: str = "R-01",
    *,
    likelihood: int = 4,
    impact: int = 4,
    residual_likelihood: int = 3,
    residual_impact: int = 4,
    owner: str = "Owner A",
    option: str = "Mitigate",
    exposure: str = "internal",
    controls: tuple[str, ...] = ("Control X",),
    title: str | None = None,
) -> Risk:
    return Risk(
        id=rid,
        title=title or f"Risk {rid}",
        asset="Asset",
        likelihood=likelihood,
        impact=impact,
        existing_controls="",
        residual_likelihood=residual_likelihood,
        residual_impact=residual_impact,
        owner=owner,
        treatment_option=option,
        exposure=exposure,
        planned_controls=controls,
    )


def make_catalogue(*entries: tuple[str, int, str, int]) -> dict[str, Treatment]:
    return {
        name.lower(): Treatment(control=name, effort=effort, cost_band=cost, time_to_implement_weeks=weeks)
        for name, effort, cost, weeks in entries
    }


@pytest.fixture
def example_paths() -> tuple[Path, Path]:
    return EXAMPLES / "northwind-register.csv", EXAMPLES / "northwind-treatments.csv"
