# Risk Treatment Plan Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![CI](https://github.com/bizidwassim-design/risk-treatment-plan-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/bizidwassim-design/risk-treatment-plan-generator/actions/workflows/ci.yml) [![Fictional data](https://img.shields.io/badge/sample%20data-fictional-informational)](SECURITY.md)

A small Python command-line tool that turns a **risk register** (CSV) and an optional **treatment catalogue**
(CSV) into a prioritised, wave-based **risk treatment plan** — Markdown with a Mermaid Gantt chart, CSV for
your ticketing tool, and an Excel workbook for the management review. One formula, three waves, zero guesswork
about "what do we fix first". Python 3.10+, no dependency except `openpyxl` for the workbook.

> 🇫🇷 Résumé en français en bas de page.

## Layout

```
rtp.py                    Entry point: python rtp.py register.csv --treatments treatments.csv --out output
rtp/                      The package (also runs as python -m rtp)
  reader.py               CSV reading and validation
  scoring.py              Bands, exposure weight, priority score, quick wins
  planning.py             Ranking, waves by effort budget, owner workload
  render_md.py            plan.md with Mermaid gantt
  render_csv.py           plan.csv (LF, rank order)
  render_xlsx.py          plan.xlsx (openpyxl, wave columns, conditional formatting, no macros)
docs/                     input-format.md · method.md
examples/                 northwind-register.csv (15 fictional risks) · northwind-treatments.csv (15 controls)
examples/output/          plan.md · plan.csv · plan.xlsx generated from the example, kept current by CI
tests/                    pytest: scoring, waves, quick wins, reader, determinism (43 tests)
```

## Quick start

```bash
pip install openpyxl            # only needed for plan.xlsx; use --no-xlsx without it
python rtp.py examples/northwind-register.csv \
    --treatments examples/northwind-treatments.csv \
    --out examples/output --title "Northwind Logistics"
```

```
15 risks -> 14 planned, 2 quick wins, 3 waves; wrote plan.md, plan.csv, plan.xlsx to examples/output
```

Then open [`examples/output/plan.md`](examples/output/plan.md) — GitHub renders the Gantt chart — or
`examples/output/plan.xlsx`.

To use your own register: export the `04_Risk_Register` sheet of the
[Application Risk Assessment Template](https://github.com/bizidwassim-design/application-risk-assessment-template)
to CSV, add an `exposure` and a `planned_control` column, list the controls with their effort in a `treatments.csv`,
and run the same command. The column rules are in [`docs/input-format.md`](docs/input-format.md).

### Options

| Flag | Default | Effect |
|------|---------|--------|
| `--treatments FILE` | none | Treatment catalogue: effort 1–5, cost band, weeks per control |
| `--out DIR` | `output` | Where `plan.md`, `plan.csv`, `plan.xlsx` are written |
| `--title TEXT` | `Risk treatment plan` | Title in the Markdown and workbook |
| `--start-date YYYY-MM-DD` | `2026-01-05` | First day of Wave 1 (fixed default keeps output reproducible) |
| `--wave-budget N` | `12` | Effort points per wave |
| `--waves N` | `3` | Number of waves; the last one takes whatever is left |
| `--quick-win-score N` | `10` | Minimum residual score for a quick win |
| `--quick-win-effort N` | `2` | Maximum effort for a quick win |
| `--no-xlsx` | | Skip the workbook (no openpyxl needed) |

## What's inside

| Piece | What it does |
|-------|--------------|
| **Priority score** | `residual score × exposure weight ÷ effort`. Residual = residual likelihood × residual impact on the 5×5 grid (Low 1–4 · Medium 5–9 · High 10–16 · Critical 17–25). Exposure: internet 1.5 · partner 1.25 · internal 1.0 · isolated 0.75. |
| **Quick wins** | Residual ≥ 10 and effort ≤ 2 — High or Critical exposure you can remove in days. Own table at the top of the plan. |
| **Waves** | Risks are placed in rank order until the cumulative effort reaches the wave budget; Wave 3 takes the rest. Dates run back to back; a wave lasts as long as its slowest control. |
| **Owner workload** | Risks, planned effort, Wave 1 items and quick wins per owner; owners carrying more than one wave budget are flagged. |
| **Accepted risks** | `Accept` rows are listed with their existing controls and never scheduled. |
| **plan.md** | Summary, quick wins, one table per wave, accepted risks, owner workload, Mermaid Gantt, warnings, method note. |
| **plan.csv** | 21 columns, one row per risk in rank order, LF line endings — stable in Git and easy to import. |
| **plan.xlsx** | `Plan` sheet with colour-coded ratings, bold priority, green quick wins, one filled cell per wave (value = weeks), autofilter and frozen panes; `Owners` and `Method` sheets. Timestamps pinned so the binary only changes when the plan does. |
| **Validation** | Every input problem is reported at once with file and line; warnings for residual > inherent and for controls missing from the catalogue. |

The full reasoning, with worked numbers from the example, is in [`docs/method.md`](docs/method.md).

## Design choices

* **Residual, not inherent, drives the plan.** The inherent score tells you how bad the scenario is without controls; the residual score tells you where you stand today. Only the second one says what to do next.
* **Divide by effort.** A treatment plan that puts five 16-week programmes in Wave 1 is not a plan. Dividing by effort gives the organisation visible progress in the first quarter while the programmes get funded.
* **Exposure as a multiplier, not a column to argue about.** Four values, explicit weights, documented. Change them in `rtp/models.py` if your context differs.
* **Greedy waves with a budget, not an optimiser.** The result is easy to explain in a steering committee: "we go down the list until the quarter is full". Re-plan by moving the numbers between wave columns in the workbook.
* **Deterministic by construction.** Fixed default start date, two-decimal rounding, explicit tie-breaks, pinned workbook timestamps. CI regenerates the example and fails if anything drifts.
* **Standard library + openpyxl.** No pandas, no templates, nothing to pin. The whole package is about 1,200 lines, docstrings included, that you can read in an afternoon.

## Related repositories

| Repository | Relationship |
|------------|--------------|
| [application-risk-assessment-template](https://github.com/bizidwassim-design/application-risk-assessment-template) | Where the register comes from — same 5×5 bands, same inherent/residual scoring |
| [iso27001-iso42001-toolkit](https://github.com/bizidwassim-design/iso27001-iso42001-toolkit) | Risk-treatment-plan and Statement-of-Applicability templates that the generated plan feeds (ISO/IEC 27001 clause 6.1.3) |
| [grc-control-crosswalk](https://github.com/bizidwassim-design/grc-control-crosswalk) | Map each planned control to ISO 27001 Annex A, NIST CSF 2.0, CIS v8 and SOC 2 |
| [ciso-executive-dashboard](https://github.com/bizidwassim-design/ciso-executive-dashboard) | Report the wave progress and residual-risk trend to the board |
| [soc-detection-playbooks](https://github.com/bizidwassim-design/soc-detection-playbooks) | Detection-side controls (SIEM onboarding, EDR) that often appear as treatments |
| [public-scripts](https://github.com/bizidwassim-design/public-scripts) | Scripts that implement several of the example controls (Conditional Access, access reviews) |

## Contributing

Bug reports, extra renderers (HTML, JSON), dependency-aware scheduling and translations are welcome —
see [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).

```bash
pip install openpyxl pytest
pytest
```

## Disclaimer

A planning aid, not a risk decision. Scores are only as good as the register behind them; the waves are a proposal
for the risk owners and management to approve, amend or reject. All sample data is fictional ("Northwind Logistics").

## AI assistance

Built with Claude Code as a coding and writing assistant, which is why it appears as a co-author on some commits.
**Editor and reviewer: Wassim Bizid**, who set the scope, the frameworks and the GRC approach, edited the content
and decided what was published. Automated tests in CI check the published outputs. This is a maintainer review,
not an independent one.

## License

[MIT](LICENSE) — free to use, copy, modify and redistribute.

---

## 🇫🇷 Résumé

Outil en ligne de commande (Python 3.10+, seule dépendance : `openpyxl`) qui transforme un **registre des risques**
(CSV) et un catalogue de traitements optionnel en **plan de traitement des risques** priorisé : score de priorité
= score résiduel × poids d'exposition ÷ effort, détection des gains rapides, répartition en trois vagues selon un
budget d'effort, charge par responsable. Produit `plan.md` (avec diagramme de Gantt Mermaid), `plan.csv` et
`plan.xlsx` (mise en forme conditionnelle, sans macro), de façon totalement reproductible. Mêmes bandes 5×5
que le modèle d'évaluation des risques applicatifs. Exemple fictif « Northwind Logistics » avec 15 risques ; tests pytest ; licence MIT.
