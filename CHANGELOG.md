# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-10-31

### Added
- `rtp` package and `rtp.py` entry point: CSV register + optional treatment catalogue → `plan.md`, `plan.csv`, `plan.xlsx`.
- Priority score `residual × exposure weight ÷ effort`, quick-win detection, three waves by effort budget, owner workload table.
- Mermaid Gantt chart in the Markdown plan; Excel workbook with wave columns and conditional formatting (openpyxl, no macros).
- Input validation that reports every problem at once; warnings for residual > inherent and unknown controls.
- Fictional "Northwind Logistics" example (15 risks, 15 controls) with committed, reproducible outputs.
- 43 pytest tests (scoring, waves, quick wins, reader, determinism) and CI that regenerates the example and diffs it.
- `SECURITY.md`, Dependabot for GitHub Actions, this changelog.
