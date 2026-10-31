from __future__ import annotations

from pathlib import Path

import pytest

from rtp.cli import main
from rtp.reader import InputError, read_register, read_treatments

HEADER = "id,title,asset,likelihood,impact,existing_controls,residual_likelihood,residual_impact,owner,treatment_option"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_minimal_register_without_optional_columns(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.csv", HEADER + "\nR-1,Title,Asset,4,4,none,3,3,Owner,Mitigate\n")
    risks, warnings = read_register(p)
    assert len(risks) == 1
    assert risks[0].exposure == "internal" and risks[0].planned_controls == ()
    assert any("no planned_control" in w for w in warnings)


def test_header_names_are_normalised(tmp_path: Path) -> None:
    header = "ID,Title,Asset,Likelihood,Impact,Existing Controls,Residual-Likelihood,Residual Impact,Owner,Treatment Option"
    p = _write(tmp_path, "r.csv", header + "\nR-1,Title,Asset,4,4,none,3,3,Owner,mitigate\n")
    risks, _ = read_register(p)
    assert risks[0].treatment_option == "Mitigate"


def test_missing_column_is_an_error(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.csv", "id,title\nR-1,T\n")
    with pytest.raises(InputError, match="missing column"):
        read_register(p)


def test_all_row_errors_are_reported_together(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        "r.csv",
        HEADER + "\nR-1,T,A,6,4,,3,3,O,Mitigate\nR-1,T,A,4,x,,3,3,O,Ignore\n",
    )
    with pytest.raises(InputError) as exc:
        read_register(p)
    msg = str(exc.value)
    assert "likelihood must be between 1 and 5" in msg
    assert "impact must be a whole number" in msg
    assert "duplicate id" in msg
    assert "treatment_option must be one of" in msg


def test_residual_above_inherent_is_a_warning_not_an_error(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.csv", HEADER + ",planned_control\nR-1,T,A,2,2,,4,4,O,Mitigate,X\n")
    risks, warnings = read_register(p)
    assert len(risks) == 1 and any("higher than inherent" in w for w in warnings)


def test_unknown_exposure_is_an_error(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.csv", HEADER + ",exposure\nR-1,T,A,2,2,,2,2,O,Mitigate,dmz\n")
    with pytest.raises(InputError, match="exposure must be one of"):
        read_register(p)


def test_treatments_validation(tmp_path: Path) -> None:
    p = _write(tmp_path, "t.csv", "control,effort,cost_band,time_to_implement_weeks\nA,9,Cheap,0\nA,1,Low,1\n")
    with pytest.raises(InputError) as exc:
        read_treatments(p)
    msg = str(exc.value)
    assert "effort must be between 1 and 5" in msg
    assert "cost_band must be one of" in msg
    assert "duplicate control" in msg
    assert read_treatments(None) == {}


def test_cli_exit_codes(tmp_path: Path, example_paths, capsys) -> None:
    register, treatments = example_paths
    assert main([str(register), "-t", str(treatments), "-o", str(tmp_path / "ok"), "-q"]) == 0
    assert (tmp_path / "ok" / "plan.xlsx").exists()
    bad = _write(tmp_path, "bad.csv", HEADER + "\nR-1,T,A,0,4,,3,3,O,Mitigate\n")
    assert main([str(bad), "-o", str(tmp_path / "bad")]) == 2
    assert "likelihood" in capsys.readouterr().err
    assert main([str(tmp_path / "missing.csv"), "-o", str(tmp_path / "x")]) == 2
