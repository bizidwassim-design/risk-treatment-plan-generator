# Contributing

Thanks for helping improve this tool. Bug reports, better documentation, new renderers and smarter scheduling
are all welcome.

## Ground rules

* **Fictional data only.** Example registers use "Northwind Logistics", "Contoso" or "Fabrikam". Never commit real
  risks, owners' names, hostnames, client names or anything from a real assessment.
* **Standard library + openpyxl.** Do not add dependencies. `openpyxl` is only imported by `render_xlsx.py` so the
  tool keeps working with `--no-xlsx` when it is absent.
* **Deterministic output.** Same inputs, same bytes. No `datetime.now()`, no dict-order surprises, no float noise:
  round where values are printed and add an explicit final tie-break on `id` wherever you sort.
* **Python 3.10+**, `from __future__ import annotations`, type hints, `#!/usr/bin/env python3` on entry points.
* Be kind — see the [Code of Conduct](CODE_OF_CONDUCT.md).

## Development loop

```bash
pip install openpyxl pytest
pytest                                    # 43 tests: scoring, waves, quick wins, reader, determinism
python rtp.py examples/northwind-register.csv -t examples/northwind-treatments.csv \
    -o examples/output --title "Northwind Logistics"
git diff --stat examples/output           # CI fails if plan.md / plan.csv drift from the committed example
```

If you change scoring, ranking, waves or any renderer, **regenerate `examples/output/` and commit it** together with
the code. `plan.xlsx` is binary but reproducible, so it only changes when the plan does.

## Where things live

| Change | File |
|--------|------|
| Bands, exposure weights, allowed treatment options, cost bands | `rtp/models.py` |
| Priority formula, quick-win rule, catalogue lookup | `rtp/scoring.py` |
| Ranking order, wave filling, dates, owner workload | `rtp/planning.py` |
| Column validation and error messages | `rtp/reader.py` |
| Output layout | `rtp/render_md.py`, `rtp/render_csv.py`, `rtp/render_xlsx.py` |
| Flags | `rtp/cli.py` |

## Ideas that would be welcome

* A `--dependencies` file so a control can be forced after another one.
* An HTML or JSON renderer.
* A `--max-weeks` per wave as an alternative to the effort budget.
* Translations of `docs/` and of the Markdown headings.

## Making a change

1. Open an issue describing the problem or idea (optional for small fixes).
2. Fork, branch (`fix/wave-dates`, `feat/json-output`).
3. Add or update tests in `tests/`; keep the suite green.
4. Regenerate the example output if anything in it changes.
5. Open a pull request explaining what changed and why.

## Licensing of contributions

By contributing you agree that your work is released under the repository's [MIT License](LICENSE).
