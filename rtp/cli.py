"""Command-line interface.

    python rtp.py REGISTER.csv [--treatments TREATMENTS.csv] [--out DIR] [options]
    python -m rtp REGISTER.csv ...
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .planning import DEFAULT_START_DATE, DEFAULT_WAVE_BUDGET, DEFAULT_WAVE_COUNT, build_plan
from .reader import InputError, read_register, read_treatments
from .render_csv import render_csv
from .render_md import render_md
from .scoring import DEFAULT_QUICK_WIN_EFFORT, DEFAULT_QUICK_WIN_SCORE


def _date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not an ISO date (YYYY-MM-DD)") from None


def _positive(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rtp",
        description="Generate a prioritised risk treatment plan (Markdown, CSV, Excel) from a risk register.",
    )
    p.add_argument("register", type=Path, help="risk register CSV (see docs/input-format.md)")
    p.add_argument("-t", "--treatments", type=Path, default=None, help="treatment catalogue CSV (optional)")
    p.add_argument("-o", "--out", type=Path, default=Path("output"), help="output directory (default: ./output)")
    p.add_argument("--title", default="Risk treatment plan", help="plan title used in the Markdown and workbook")
    p.add_argument(
        "--start-date",
        type=_date,
        default=DEFAULT_START_DATE,
        help=f"first day of Wave 1, ISO format (default: {DEFAULT_START_DATE.isoformat()}, fixed for reproducibility)",
    )
    p.add_argument("--wave-budget", type=_positive, default=DEFAULT_WAVE_BUDGET, help=f"effort points per wave (default {DEFAULT_WAVE_BUDGET})")
    p.add_argument("--waves", type=_positive, default=DEFAULT_WAVE_COUNT, help=f"number of waves (default {DEFAULT_WAVE_COUNT})")
    p.add_argument("--quick-win-score", type=_positive, default=DEFAULT_QUICK_WIN_SCORE, help=f"minimum residual score for a quick win (default {DEFAULT_QUICK_WIN_SCORE})")
    p.add_argument("--quick-win-effort", type=_positive, default=DEFAULT_QUICK_WIN_EFFORT, help=f"maximum effort for a quick win (default {DEFAULT_QUICK_WIN_EFFORT})")
    p.add_argument("--no-xlsx", action="store_true", help="skip the Excel workbook (no openpyxl needed)")
    p.add_argument("-q", "--quiet", action="store_true", help="print nothing but errors")
    p.add_argument("--version", action="version", version=f"rtp {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        risks, warnings = read_register(args.register)
        catalogue = read_treatments(args.treatments)
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 2
    except InputError as exc:
        print("error: input could not be used:", file=sys.stderr)
        for line in str(exc).splitlines():
            print(f"  {line}", file=sys.stderr)
        return 2

    plan = build_plan(
        risks,
        catalogue,
        title=args.title,
        start_date=args.start_date,
        wave_budget=args.wave_budget,
        wave_count=args.waves,
        quick_win_score=args.quick_win_score,
        quick_win_effort=args.quick_win_effort,
        warnings=warnings,
    )

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    render_md(plan, out / "plan.md")
    render_csv(plan, out / "plan.csv")
    written = ["plan.md", "plan.csv"]
    if not args.no_xlsx:
        try:
            from .render_xlsx import render_xlsx  # openpyxl is only needed here
        except ImportError:
            print("error: openpyxl is not installed; run 'pip install openpyxl' or pass --no-xlsx", file=sys.stderr)
            return 2
        render_xlsx(plan, out / "plan.xlsx")
        written.append("plan.xlsx")

    if not args.quiet:
        for w in plan.warnings:
            print(f"warning: {w}", file=sys.stderr)
        planned = plan.planned_items
        print(
            f"{len(plan.items)} risks -> {len(planned)} planned, {len(plan.quick_wins)} quick wins, "
            f"{sum(1 for w in plan.waves if w.items)} waves; wrote {', '.join(written)} to {out}"
        )
    return 0
