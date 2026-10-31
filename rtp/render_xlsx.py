"""plan.xlsx — Plan sheet with Gantt-like wave columns, Owners sheet, Method sheet.

Built with openpyxl, no macros. Document timestamps are pinned so the binary is
reproducible build after build.
"""
from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .models import EXPOSURE_WEIGHTS, Plan
from .render_csv import COLUMNS, item_row

NAVY = "1F3864"
FONT = "Arial"
HEADER_FONT = Font(name=FONT, bold=True, color="FFFFFF", size=10)
HEADER_FILL = PatternFill("solid", fgColor=NAVY)
BODY_FONT = Font(name=FONT, size=10)
BOLD_FONT = Font(name=FONT, size=10, bold=True)
TITLE_FONT = Font(name=FONT, size=14, bold=True, color=NAVY)
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="top")

BAND_FILLS = {
    "Low": PatternFill("solid", fgColor="C6EFCE"),
    "Medium": PatternFill("solid", fgColor="FFEB9C"),
    "High": PatternFill("solid", fgColor="F8CBAD"),
    "Critical": PatternFill("solid", fgColor="FF7C80"),
}
QUICK_WIN_FILL = PatternFill("solid", fgColor="C6EFCE")
WAVE_FILLS = {
    1: PatternFill("solid", fgColor="2E75B6"),
    2: PatternFill("solid", fgColor="5B9BD5"),
    3: PatternFill("solid", fgColor="9DC3E6"),
}
WAVE_DEFAULT_FILL = PatternFill("solid", fgColor="BDD7EE")

PLAN_HEADERS: dict[str, str] = {
    "rank": "#",
    "id": "ID",
    "title": "Risk",
    "asset": "Asset",
    "owner": "Owner",
    "treatment_option": "Option",
    "exposure": "Exposure",
    "exposure_weight": "Weight",
    "inherent_score": "Inherent",
    "inherent_band": "Inherent band",
    "residual_score": "Residual",
    "residual_band": "Residual band",
    "planned_control": "Planned control",
    "effort": "Effort",
    "cost_band": "Cost",
    "time_to_implement_weeks": "Weeks",
    "priority_score": "Priority",
    "quick_win": "Quick win",
    "wave": "Wave",
    "wave_start": "Start",
    "wave_end": "End",
}
NUMERIC = {"rank", "exposure_weight", "inherent_score", "residual_score", "effort", "time_to_implement_weeks", "priority_score", "wave"}
WIDTHS = {
    "rank": 5, "id": 8, "title": 46, "asset": 24, "owner": 26, "treatment_option": 10, "exposure": 10,
    "exposure_weight": 8, "inherent_score": 9, "inherent_band": 13, "residual_score": 9, "residual_band": 13,
    "planned_control": 40, "effort": 8, "cost_band": 10, "time_to_implement_weeks": 8, "priority_score": 9,
    "quick_win": 10, "wave": 7, "wave_start": 12, "wave_end": 12,
}


def _header(ws, row: int, labels: list[str]) -> None:
    for col, label in enumerate(labels, start=1):
        c = ws.cell(row=row, column=col, value=label)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        c.border = BORDER
    ws.row_dimensions[row].height = 30


def _plan_sheet(wb: Workbook, plan: Plan) -> None:
    ws = wb.active
    ws.title = "Plan"
    ws.sheet_view.showGridLines = False
    ws["A1"] = f"{plan.title} — risk treatment plan"
    ws["A1"].font = TITLE_FONT
    ws["A2"] = (
        f"Start {plan.start_date.isoformat()} · wave budget {plan.wave_budget} effort points · "
        f"quick win = residual ≥ {plan.quick_win_score} and effort ≤ {plan.quick_win_effort} · "
        "priority = residual × exposure weight ÷ effort"
    )
    ws["A2"].font = Font(name=FONT, size=9, italic=True, color="595959")

    wave_numbers = [w.number for w in plan.waves]
    labels = [PLAN_HEADERS[c] for c in COLUMNS] + [f"Wave {n}" for n in wave_numbers]
    header_row = 4
    _header(ws, header_row, labels)
    first_wave_col = len(COLUMNS) + 1

    for r_off, item in enumerate(plan.items, start=1):
        row = header_row + r_off
        values = item_row(item)
        for col, key in enumerate(COLUMNS, start=1):
            raw = values[key]
            value: object = raw
            if key in NUMERIC and raw != "":
                value = float(raw) if key in ("exposure_weight", "priority_score") else int(raw)
            cell = ws.cell(row=row, column=col, value=value)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = CENTER if key in NUMERIC or key in ("quick_win", "exposure") else WRAP
            if key == "priority_score":
                cell.number_format = "0.00"
                cell.font = BOLD_FONT
        # Gantt-like columns: weeks of work shown in the wave the item belongs to.
        for i, n in enumerate(wave_numbers):
            cell = ws.cell(row=row, column=first_wave_col + i, value=item.weeks if item.wave == n else None)
            cell.font = Font(name=FONT, size=10, bold=True, color="FFFFFF")
            cell.alignment = CENTER
            cell.border = BORDER
            if item.wave == n:
                cell.fill = WAVE_FILLS.get(n, WAVE_DEFAULT_FILL)

    last_row = header_row + len(plan.items)
    col_of = {key: i + 1 for i, key in enumerate(COLUMNS)}
    for key, width in WIDTHS.items():
        ws.column_dimensions[get_column_letter(col_of[key])].width = width
    for i in range(len(wave_numbers)):
        ws.column_dimensions[get_column_letter(first_wave_col + i)].width = 9

    ws.freeze_panes = ws.cell(row=header_row + 1, column=4)
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(labels))}{last_row}"

    # Conditional formatting: rating bands, quick wins, wave cells
    for key in ("inherent_band", "residual_band"):
        letter = get_column_letter(col_of[key])
        rng = f"{letter}{header_row + 1}:{letter}{last_row}"
        for name, fill in BAND_FILLS.items():
            ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=[f'"{name}"'], fill=fill))
    qw = get_column_letter(col_of["quick_win"])
    ws.conditional_formatting.add(
        f"{qw}{header_row + 1}:{qw}{last_row}",
        CellIsRule(operator="equal", formula=['"yes"'], fill=QUICK_WIN_FILL, font=Font(name=FONT, bold=True, color="006100")),
    )
    pr = get_column_letter(col_of["priority_score"])
    ws.conditional_formatting.add(
        f"{pr}{header_row + 1}:{pr}{last_row}",
        FormulaRule(formula=[f"{pr}{header_row + 1}>=10"], font=Font(name=FONT, bold=True, color="9C0006")),
    )
    # Any wave cell that holds a number is highlighted even after a user edits the wave column.
    for i, n in enumerate(wave_numbers):
        wl = get_column_letter(first_wave_col + i)
        ws.conditional_formatting.add(
            f"{wl}{header_row + 1}:{wl}{last_row}",
            FormulaRule(formula=[f"ISNUMBER({wl}{header_row + 1})"], fill=WAVE_FILLS.get(n, WAVE_DEFAULT_FILL)),
        )


def _owners_sheet(wb: Workbook, plan: Plan) -> None:
    ws = wb.create_sheet("Owners")
    ws.sheet_view.showGridLines = False
    ws["A1"] = "Owner workload"
    ws["A1"].font = TITLE_FONT
    labels = ["Owner", "Risks", "Planned", "Effort", "In Wave 1", "Quick wins", "Highest residual", "Over one wave budget?"]
    _header(ws, 3, labels)
    for r_off, o in enumerate(plan.owners, start=4):
        values = [o.owner, o.risks, o.planned, o.effort, o.wave1, o.quick_wins, o.highest_band,
                  "yes" if o.effort > plan.wave_budget else "no"]
        for col, v in enumerate(values, start=1):
            c = ws.cell(row=r_off, column=col, value=v)
            c.font = BODY_FONT
            c.border = BORDER
            c.alignment = WRAP if col == 1 else CENTER
    last = 3 + len(plan.owners)
    for name, fill in BAND_FILLS.items():
        ws.conditional_formatting.add(f"G4:G{last}", CellIsRule(operator="equal", formula=[f'"{name}"'], fill=fill))
    ws.conditional_formatting.add(
        f"H4:H{last}", CellIsRule(operator="equal", formula=['"yes"'], fill=PatternFill("solid", fgColor="FFC7CE"))
    )
    for col, width in enumerate([30, 8, 9, 8, 10, 11, 16, 20], start=1):
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A4"


def _method_sheet(wb: Workbook, plan: Plan) -> None:
    ws = wb.create_sheet("Method")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 90
    ws["A1"] = "How this plan was computed"
    ws["A1"].font = TITLE_FONT
    rows = [
        ("Formula", "priority = residual score × exposure weight ÷ effort"),
        ("Residual score", "residual likelihood (1–5) × residual impact (1–5) = 1 to 25"),
        ("Rating bands", "Low 1–4 · Medium 5–9 · High 10–16 · Critical 17–25"),
        ("Exposure weights", " · ".join(f"{k} {v:g}" for k, v in EXPOSURE_WEIGHTS.items())),
        ("Effort", "1 trivial · 2 small · 3 project · 4 large project · 5 programme (from treatments.csv)"),
        ("Quick win", f"residual score ≥ {plan.quick_win_score} and effort ≤ {plan.quick_win_effort}"),
        ("Ranking", "priority desc, then residual score desc, then effort asc, then ID"),
        ("Waves", f"filled in rank order until the cumulative effort reaches {plan.wave_budget}; the last wave takes the rest"),
        ("Dates", f"waves run back to back from {plan.start_date.isoformat()}; a wave lasts as long as its slowest control"),
        ("Accepted risks", "listed with no wave; acceptance needs an approver and a review date"),
        ("Wave columns", "the number in a wave column is the weeks of work for that treatment; move it to re-plan by hand"),
    ]
    for r, (k, v) in enumerate(rows, start=3):
        a = ws.cell(row=r, column=1, value=k)
        a.font = BOLD_FONT
        a.alignment = WRAP
        b = ws.cell(row=r, column=2, value=v)
        b.font = BODY_FONT
        b.alignment = WRAP
    if plan.warnings:
        start = 3 + len(rows) + 1
        ws.cell(row=start, column=1, value="Warnings").font = BOLD_FONT
        for i, w in enumerate(plan.warnings):
            c = ws.cell(row=start + i, column=2, value=w)
            c.font = BODY_FONT
            c.alignment = WRAP


def _rezip_with_fixed_timestamps(blob: bytes, path: Path, stamp: tuple[int, int, int, int, int, int]) -> None:
    """Rewrite the .xlsx (a zip) so every entry carries the same timestamp.

    openpyxl stamps zip entries with the wall clock, which would make the file
    change on every build even when nothing in the plan changed.
    """
    src = zipfile.ZipFile(io.BytesIO(blob))
    iso = "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(*stamp)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info in sorted(src.infolist(), key=lambda i: i.filename):
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                # openpyxl overwrites dcterms:modified with the wall clock on every save.
                data = re.sub(
                    rb"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                    lambda m: m.group(1) + iso.encode() + m.group(2),
                    data,
                )
            new = zipfile.ZipInfo(info.filename, date_time=stamp)
            new.compress_type = zipfile.ZIP_DEFLATED
            new.external_attr = info.external_attr
            dst.writestr(new, data)


def render_xlsx(plan: Plan, path: Path) -> None:
    wb = Workbook()
    fixed = datetime(2026, 1, 1, 0, 0, 0)
    wb.properties.creator = "rtp"
    wb.properties.lastModifiedBy = "rtp"
    wb.properties.created = fixed
    wb.properties.modified = fixed
    _plan_sheet(wb, plan)
    _owners_sheet(wb, plan)
    _method_sheet(wb, plan)
    buffer = io.BytesIO()
    wb.save(buffer)
    _rezip_with_fixed_timestamps(buffer.getvalue(), path, (2026, 1, 1, 0, 0, 0))
