"""Data classes shared by the reader, the scorer, the planner and the renderers."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

# --- Constants -------------------------------------------------------------

#: Risk rating bands on the 5 x 5 Likelihood x Impact grid (1..25).
#: Same bands as the Application Risk Assessment Template.
BANDS: tuple[tuple[str, int, int], ...] = (
    ("Low", 1, 4),
    ("Medium", 5, 9),
    ("High", 10, 16),
    ("Critical", 17, 25),
)

#: Exposure of the asset the risk sits on. Weights are multiplied into the
#: priority score: an internet-facing weakness of the same residual score is
#: planned before an isolated one.
EXPOSURE_WEIGHTS: dict[str, float] = {
    "internet": 1.5,
    "partner": 1.25,
    "internal": 1.0,
    "isolated": 0.75,
}
DEFAULT_EXPOSURE = "internal"

#: Treatment options accepted in the register (ISO/IEC 27001 clause 6.1.3 vocabulary).
TREATMENT_OPTIONS: tuple[str, ...] = ("Mitigate", "Transfer", "Avoid", "Accept")

#: Treatment options that do not need a planned control and are therefore not
#: placed in a wave. They are still listed in the plan for completeness.
UNPLANNED_OPTIONS: frozenset[str] = frozenset({"Accept"})

#: Cost bands accepted in treatments.csv, lowest to highest.
COST_BANDS: tuple[str, ...] = ("Low", "Medium", "High", "Very high")

DEFAULT_EFFORT = 3
DEFAULT_WEEKS = 6
DEFAULT_COST_BAND = "Unknown"


# --- Input records -----------------------------------------------------------


@dataclass(frozen=True)
class Risk:
    """One row of the risk register."""

    id: str
    title: str
    asset: str
    likelihood: int
    impact: int
    existing_controls: str
    residual_likelihood: int
    residual_impact: int
    owner: str
    treatment_option: str
    exposure: str = DEFAULT_EXPOSURE
    planned_controls: tuple[str, ...] = ()

    @property
    def inherent_score(self) -> int:
        return self.likelihood * self.impact

    @property
    def residual_score(self) -> int:
        return self.residual_likelihood * self.residual_impact


@dataclass(frozen=True)
class Treatment:
    """One row of the treatment catalogue (treatments.csv)."""

    control: str
    effort: int
    cost_band: str
    time_to_implement_weeks: int


# --- Output records ----------------------------------------------------------


@dataclass
class PlanItem:
    """A risk after scoring and planning. One row of plan.csv."""

    risk: Risk
    effort: int
    cost_band: str
    weeks: int
    exposure_weight: float
    priority_score: float
    quick_win: bool
    controls_found: tuple[str, ...] = ()
    controls_missing: tuple[str, ...] = ()
    rank: int = 0
    wave: int | None = None  # None = not planned (accepted risk)
    wave_start: date | None = None
    wave_end: date | None = None

    @property
    def planned(self) -> bool:
        return self.wave is not None

    @property
    def wave_label(self) -> str:
        return f"Wave {self.wave}" if self.wave else "Not planned"


@dataclass
class Wave:
    number: int
    items: list[PlanItem] = field(default_factory=list)
    start: date | None = None
    end: date | None = None

    @property
    def effort(self) -> int:
        return sum(i.effort for i in self.items)

    @property
    def weeks(self) -> int:
        return max((i.weeks for i in self.items), default=0)


@dataclass
class OwnerLoad:
    owner: str
    risks: int
    planned: int
    effort: int
    wave1: int
    quick_wins: int
    highest_band: str


@dataclass
class Plan:
    title: str
    start_date: date
    wave_budget: int
    quick_win_score: int
    quick_win_effort: int
    items: list[PlanItem]
    waves: list[Wave]
    owners: list[OwnerLoad]
    warnings: list[str] = field(default_factory=list)

    @property
    def planned_items(self) -> list[PlanItem]:
        return [i for i in self.items if i.planned]

    @property
    def unplanned_items(self) -> list[PlanItem]:
        return [i for i in self.items if not i.planned]

    @property
    def quick_wins(self) -> list[PlanItem]:
        return [i for i in self.items if i.quick_win]
