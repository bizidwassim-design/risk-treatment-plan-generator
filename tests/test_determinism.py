from __future__ import annotations

import filecmp
from pathlib import Path

from rtp.cli import main

ROOT = Path(__file__).resolve().parent.parent
COMMITTED = ROOT / "examples" / "output"


def _run(out: Path, example_paths) -> None:
    register, treatments = example_paths
    code = main(
        [str(register), "--treatments", str(treatments), "--out", str(out), "--title", "Northwind Logistics", "--quiet"]
    )
    assert code == 0


def test_two_runs_produce_identical_bytes(tmp_path: Path, example_paths) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    _run(a, example_paths)
    _run(b, example_paths)
    for name in ("plan.md", "plan.csv", "plan.xlsx"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), f"{name} is not deterministic"


def test_committed_example_output_is_current(tmp_path: Path, example_paths) -> None:
    _run(tmp_path, example_paths)
    for name in ("plan.md", "plan.csv"):
        assert filecmp.cmp(tmp_path / name, COMMITTED / name, shallow=False), (
            f"examples/output/{name} is stale — regenerate it (see README)"
        )


def test_outputs_use_lf_line_endings(tmp_path: Path, example_paths) -> None:
    _run(tmp_path, example_paths)
    for name in ("plan.md", "plan.csv"):
        assert b"\r\n" not in (tmp_path / name).read_bytes()


def test_row_order_is_independent_of_register_order(tmp_path: Path, example_paths) -> None:
    register, treatments = example_paths
    lines = register.read_text(encoding="utf-8").splitlines()
    shuffled = tmp_path / "shuffled.csv"
    shuffled.write_text("\n".join([lines[0]] + list(reversed(lines[1:]))) + "\n", encoding="utf-8")
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    assert main([str(register), "-t", str(treatments), "-o", str(out_a), "-q", "--no-xlsx"]) == 0
    assert main([str(shuffled), "-t", str(treatments), "-o", str(out_b), "-q", "--no-xlsx"]) == 0
    assert (out_a / "plan.csv").read_bytes() == (out_b / "plan.csv").read_bytes()
