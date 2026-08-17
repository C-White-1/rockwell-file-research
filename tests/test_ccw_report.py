"""Synthetic unit tests for the CCW report parser helpers."""

import csv

from ccw_report import _column, _write_csv


def test_column_returns_excel_column_letters() -> None:
    assert _column("A1") == "A"
    assert _column("BC42") == "BC"


def test_write_csv_uses_union_of_row_fields(tmp_path) -> None:
    destination = tmp_path / "rows.csv"

    _write_csv(destination, [{"name": "Pump"}, {"value": "Running"}])

    with destination.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {"name": "Pump", "value": ""},
        {"name": "", "value": "Running"},
    ]
