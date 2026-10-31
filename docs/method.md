# Method

The generator answers one question: **in which order, and in which quarter, should we treat these risks?**
It does so with a single formula, a greedy scheduler and a few conventions. Everything is deterministic:
the same inputs always give the same `plan.md`, `plan.csv` and `plan.xlsx`, byte for byte.

## 1. Residual score and rating

```
residual score = residual likelihood (1–5) × residual impact (1–5)      → 1 to 25
```

| Rating | Score |
|--------|-------|
| 🟢 Low | 1–4 |
| 🟡 Medium | 5–9 |
| 🟠 High | 10–16 |
| 🔴 Critical | 17–25 |

Same bands as the [Application Risk Assessment Template](https://github.com/bizidwassim-design/application-risk-assessment-template),
so a register exported from that workbook needs no re-scoring. The plan is driven by the **residual** score:
the inherent score is shown for context only.

## 2. Priority score

```
priority = residual score × exposure weight ÷ effort
```

| Factor | Values | Why |
|--------|--------|-----|
| Exposure weight | internet **1.5** · partner **1.25** · internal **1.0** · isolated **0.75** | Two risks with the same residual score are not equally urgent: one reachable from the internet is probed every day. |
| Effort | 1 trivial · 2 small · 3 project · 4 large project · 5 programme | Dividing by effort promotes cheap fixes and demotes long programmes, which is what a treatment plan has to do to show progress in the first quarter. |

Examples from the Northwind register:

| Risk | Residual | Exposure | Effort | Priority |
|------|----------|----------|--------|----------|
| R-02 legacy authentication bypasses MFA | 12 | internet 1.5 | 1 | **18.00** |
| R-03 unpatched VPN appliance | 20 | internet 1.5 | 2 | **15.00** |
| R-01 ransomware via phishing | 15 | internal 1.0 | 3 | **5.00** |
| R-05 flat network to OT | 12 | internal 1.0 | 5 | **2.40** |

The priority score is a planning aid, not a risk rating. R-05 stays a High risk; it simply cannot be fixed in a week.

## 3. Quick wins

A risk is flagged a quick win when `residual score ≥ 10` (High or Critical) **and** `effort ≤ 2`.
Both thresholds are flags (`--quick-win-score`, `--quick-win-effort`). Quick wins are listed in their own table at
the top of `plan.md`; because low effort also lifts their priority score, they almost always land in Wave 1.

A cheap control against a Medium risk (R-13 awareness training, priority 13.5) ranks high but is **not** a quick win:
the label is reserved for things that remove a High or Critical exposure fast.

## 4. Ranking

Sort by priority score (desc), then residual score (desc), then effort (asc), then `id` (A→Z).
The last key guarantees a stable order even when two risks are identical on every number.

## 5. Waves

Waves are filled in rank order with a cumulative **effort budget** (`--wave-budget`, default 12 points).
When the next item would push the running total over the budget, the wave closes and the item opens the next one.
The last wave (`--waves`, default 3) takes everything that is left, so no risk is dropped.
An item larger than the whole budget still goes in: it opens a wave on its own.

The budget is the capacity you believe the organisation has per planning period — roughly "how many effort points
can we land in a quarter". Twelve points is four projects, or one programme and several small changes. Tune it
until Wave 1 looks like something your teams would sign up to.

`Accept` rows are never placed in a wave; they appear in a separate table with their existing controls.
Acceptance needs a named approver and a review date — the register, not the plan, should hold those.

## 6. Dates

Waves run back to back from `--start-date` (default `2026-01-05`, fixed so the committed example never changes).
A wave lasts as long as its **slowest** control (`time_to_implement_weeks`). Each item also gets its own end date
(start of its wave + its own duration), which is what the Gantt bars and the `wave_end` column show.

## 7. Owner workload

One line per `owner` with the number of risks, planned treatments, total effort, items in Wave 1, quick wins and
the highest residual rating they carry. An owner whose planned effort exceeds one wave budget is flagged in
`plan.md` and in the `Owners` sheet. That is the first thing to fix in a review meeting: a plan that gives one
team three quarters of the work is not a plan.

## 8. Outputs

| File | Use it for |
|------|-----------|
| `plan.md` | Reading, reviewing in a pull request, pasting into a wiki. Contains the Mermaid Gantt chart, rendered natively by GitHub. |
| `plan.csv` | Importing into a ticketing tool or a BI dashboard. One row per risk, rank order, LF line endings. |
| `plan.xlsx` | Management review. `Plan` sheet with colour-coded ratings, quick wins, a filled cell per wave (the number is the weeks of work), `Owners` sheet, `Method` sheet with the parameters and warnings. No macros. |

## 9. What the method does not do

* It does not compute cost–benefit in money. Cost bands are carried through for the reader, not multiplied in.
* It does not model dependencies between controls (segmentation before SIEM, for instance). Reorder by hand in the
  workbook — the wave columns are plain cells — or split the register into two runs.
* It does not replace risk acceptance decisions, management review or the Statement of Applicability.
