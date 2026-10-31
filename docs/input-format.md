# Input format

Two plain UTF-8 CSV files with a header row. Column names are matched case-insensitively and spaces or
hyphens are read as underscores, so `Residual Likelihood` and `residual_likelihood` are the same column.
A UTF-8 BOM (as written by Excel) is tolerated.

## 1. Risk register (required)

One row per risk. This is the same information the
[Application Risk Assessment Template](https://github.com/bizidwassim-design/application-risk-assessment-template)
holds in its `04_Risk_Register` sheet — export it to CSV and rename the headers if needed.

| Column | Required | Type | Rules |
|--------|----------|------|-------|
| `id` | yes | text | Unique. Keep it short (`R-07`); it appears in every table and in the Gantt chart. |
| `title` | yes | text | One sentence describing the scenario: threat + weakness + consequence. |
| `asset` | yes | text | The application, system, data set or process the risk sits on. |
| `likelihood` | yes | 1–5 | Inherent likelihood, before any control. |
| `impact` | yes | 1–5 | Inherent impact. |
| `existing_controls` | yes | text | What is already in place. May be empty. |
| `residual_likelihood` | yes | 1–5 | Likelihood after existing controls. |
| `residual_impact` | yes | 1–5 | Impact after existing controls. |
| `owner` | yes | text | Role, not a person. Drives the owner workload table. |
| `treatment_option` | yes | enum | `Mitigate`, `Transfer`, `Avoid` or `Accept` (any case). `Accept` rows are listed but not scheduled. |
| `exposure` | no | enum | `internet`, `partner`, `internal` (default) or `isolated`. Sets the exposure weight. |
| `planned_control` | no | text | Name(s) of the control(s) that will treat the risk, matching `control` in the treatment catalogue. Separate several with `;`. |

Scores are computed, never read: `inherent = likelihood × impact`, `residual = residual_likelihood × residual_impact`.

### Validation

The tool refuses to run (exit code 2) and lists **every** problem when:

* a required column is missing or the file has no data rows;
* `id` is empty or duplicated, `title` or `owner` is empty;
* a 1–5 value is not a whole number between 1 and 5;
* `treatment_option` or `exposure` is not one of the allowed values.

It runs but prints a **warning** (also written to `plan.md` and the `Method` sheet) when:

* the residual score is higher than the inherent score — almost always a scoring mistake;
* a `Mitigate`/`Transfer`/`Avoid` row has no `planned_control` — default effort 3, 6 weeks, cost `Unknown` are used;
* a `planned_control` is not found in the catalogue — same defaults.

## 2. Treatment catalogue (optional, recommended)

One row per control you might implement. Several risks can point to the same control.

| Column | Required | Type | Rules |
|--------|----------|------|-------|
| `control` | yes | text | Unique name. Matched to `planned_control` case-insensitively. |
| `effort` | yes | 1–5 | 1 trivial (a setting) · 2 small (days) · 3 project (weeks) · 4 large project (a quarter) · 5 programme (several quarters, several teams). |
| `cost_band` | yes | enum | `Low`, `Medium`, `High`, `Very high`. Calibrate the bands to your budget; the tool only orders them. |
| `time_to_implement_weeks` | yes | 1–520 | Elapsed time from start to "control is operating". Sets the length of the bar in the Gantt. |

When a risk names several controls, the plan uses the **sum of efforts** (capped at 5), the **longest** duration
and the **highest** cost band.

Without a catalogue every planned risk gets effort 3, so the priority score reduces to `residual × exposure weight ÷ 3`
and the waves are filled purely by residual score and exposure. That is still a usable first cut.

## Minimal example

```csv
id,title,asset,likelihood,impact,existing_controls,residual_likelihood,residual_impact,owner,treatment_option,exposure,planned_control
R-01,Known vulnerability on the VPN appliance exploited from the internet,Remote access gateway,5,5,Monthly patch cycle,4,5,Network Lead,Mitigate,internet,Patch SLA for internet-facing systems
R-02,HR data sent to personal e-mail,HR system,3,3,Acceptable use policy,2,3,HR Systems Owner,Accept,internal,
```

```csv
control,effort,cost_band,time_to_implement_weeks
Patch SLA for internet-facing systems,2,Low,4
```

See [`examples/northwind-register.csv`](../examples/northwind-register.csv) and
[`examples/northwind-treatments.csv`](../examples/northwind-treatments.csv) for a full fictional set.
