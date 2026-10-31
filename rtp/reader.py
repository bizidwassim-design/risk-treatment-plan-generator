"""Read and validate the two CSV inputs.

Both files are plain UTF-8 CSV with a header row. Column names are matched
case-insensitively and spaces/hyphens are treated as underscores, so
``Residual Likelihood`` and ``residual_likelihood`` are the same column.
See docs/input-format.md for the full specification.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .models import (
    COST_BANDS,
    DEFAULT_EXPOSURE,
    EXPOSURE_WEIGHTS,
    TREATMENT_OPTIONS,
    Risk,
    Treatment,
)

REQUIRED_REGISTER_COLUMNS: tuple[str, ...] = (
    "id",
    "title",
    "asset",
    "likelihood",
    "impact",
    "existing_controls",
    "residual_likelihood",
    "residual_impact",
    "owner",
    "treatment_option",
)
OPTIONAL_REGISTER_COLUMNS: tuple[str, ...] = ("exposure", "planned_control")

REQUIRED_TREATMENT_COLUMNS: tuple[str, ...] = (
    "control",
    "effort",
    "cost_band",
    "time_to_implement_weeks",
)

CONTROL_SEPARATOR = ";"


class InputError(ValueError):
    """Raised when an input file cannot be used. The message lists every problem."""


def _norm(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise InputError(f"{path}: file is empty")
        fieldnames = [_norm(f) for f in reader.fieldnames]
        rows = []
        for raw in reader:
            row = {_norm(k): (v or "").strip() for k, v in raw.items() if k is not None}
            if any(row.values()):
                rows.append(row)
    return fieldnames, rows


def _int_in_range(value: str, low: int, high: int, what: str, where: str, errors: list[str]) -> int:
    try:
        number = int(value)
    except ValueError:
        errors.append(f"{where}: {what} must be a whole number, got {value!r}")
        return low
    if not low <= number <= high:
        errors.append(f"{where}: {what} must be between {low} and {high}, got {number}")
    return number


def read_register(path: Path) -> tuple[list[Risk], list[str]]:
    """Return ``(risks, warnings)``; raise ``InputError`` on hard errors."""
    fieldnames, rows = _read_rows(path)
    missing = [c for c in REQUIRED_REGISTER_COLUMNS if c not in fieldnames]
    if missing:
        raise InputError(f"{path}: missing column(s): {', '.join(missing)}")
    if not rows:
        raise InputError(f"{path}: no risk rows found")

    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    risks: list[Risk] = []
    canonical_option = {o.lower(): o for o in TREATMENT_OPTIONS}

    for line, row in enumerate(rows, start=2):
        where = f"{path.name} line {line}"
        rid = row.get("id", "")
        if not rid:
            errors.append(f"{where}: id is empty")
        elif rid in seen:
            errors.append(f"{where}: duplicate id {rid!r}")
        seen.add(rid)
        if not row.get("title"):
            errors.append(f"{where}: title is empty")
        if not row.get("owner"):
            errors.append(f"{where}: owner is empty")

        lik = _int_in_range(row.get("likelihood", ""), 1, 5, "likelihood", where, errors)
        imp = _int_in_range(row.get("impact", ""), 1, 5, "impact", where, errors)
        rlik = _int_in_range(row.get("residual_likelihood", ""), 1, 5, "residual_likelihood", where, errors)
        rimp = _int_in_range(row.get("residual_impact", ""), 1, 5, "residual_impact", where, errors)
        if rlik * rimp > lik * imp:
            warnings.append(
                f"{where}: residual score {rlik * rimp} is higher than inherent score {lik * imp} "
                f"for {rid} — check the scoring"
            )

        option_raw = row.get("treatment_option", "")
        option = canonical_option.get(option_raw.lower())
        if option is None:
            errors.append(
                f"{where}: treatment_option must be one of {', '.join(TREATMENT_OPTIONS)}, got {option_raw!r}"
            )
            option = "Mitigate"

        exposure = (row.get("exposure") or DEFAULT_EXPOSURE).lower()
        if exposure not in EXPOSURE_WEIGHTS:
            errors.append(
                f"{where}: exposure must be one of {', '.join(EXPOSURE_WEIGHTS)}, got {row.get('exposure')!r}"
            )
            exposure = DEFAULT_EXPOSURE

        controls = tuple(
            c.strip() for c in (row.get("planned_control") or "").split(CONTROL_SEPARATOR) if c.strip()
        )
        if option not in ("Accept",) and not controls:
            warnings.append(f"{where}: {rid} is '{option}' but has no planned_control — default effort 3 applied")

        risks.append(
            Risk(
                id=rid,
                title=row.get("title", ""),
                asset=row.get("asset", ""),
                likelihood=lik,
                impact=imp,
                existing_controls=row.get("existing_controls", ""),
                residual_likelihood=rlik,
                residual_impact=rimp,
                owner=row.get("owner", ""),
                treatment_option=option,
                exposure=exposure,
                planned_controls=controls,
            )
        )

    if errors:
        raise InputError("\n".join(errors))
    return risks, warnings


def read_treatments(path: Path | None) -> dict[str, Treatment]:
    """Return the catalogue keyed by lower-cased control name. Empty if no path."""
    if path is None:
        return {}
    fieldnames, rows = _read_rows(path)
    missing = [c for c in REQUIRED_TREATMENT_COLUMNS if c not in fieldnames]
    if missing:
        raise InputError(f"{path}: missing column(s): {', '.join(missing)}")

    errors: list[str] = []
    catalogue: dict[str, Treatment] = {}
    canonical_band = {b.lower(): b for b in COST_BANDS}
    for line, row in enumerate(rows, start=2):
        where = f"{path.name} line {line}"
        name = row.get("control", "")
        if not name:
            errors.append(f"{where}: control is empty")
            continue
        key = name.lower()
        if key in catalogue:
            errors.append(f"{where}: duplicate control {name!r}")
        effort = _int_in_range(row.get("effort", ""), 1, 5, "effort", where, errors)
        weeks = _int_in_range(row.get("time_to_implement_weeks", ""), 1, 520, "time_to_implement_weeks", where, errors)
        band_raw = row.get("cost_band", "")
        cost = canonical_band.get(band_raw.lower())
        if cost is None:
            errors.append(f"{where}: cost_band must be one of {', '.join(COST_BANDS)}, got {band_raw!r}")
            cost = COST_BANDS[0]
        catalogue[key] = Treatment(control=name, effort=effort, cost_band=cost, time_to_implement_weeks=weeks)

    if errors:
        raise InputError("\n".join(errors))
    return catalogue
