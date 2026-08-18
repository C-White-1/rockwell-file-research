"""Synthetic unit tests for the CCW report parser helpers."""

import csv
from pathlib import Path

import pytest

from rockwell_file_research.ccw.cli import main
from rockwell_file_research.ccw.errors import (
    UnsupportedWorkbookError,
    WorkbookReadError,
)
from rockwell_file_research.ccw.export import write_csv
from rockwell_file_research.ccw.normalize import alarms
from rockwell_file_research.ccw.reporting import build_report
from rockwell_file_research.ccw.types import Workbook
from rockwell_file_research.ccw.validation import validate_workbook
from rockwell_file_research.ccw.xlsx import column_name, read_workbook
from tests.fixture_factory import build_synthetic_ccw_workbook


def test_column_returns_excel_column_letters() -> None:
    assert column_name("A1") == "A"
    assert column_name("BC42") == "BC"


def test_write_csv_uses_union_of_row_fields(tmp_path) -> None:
    destination = tmp_path / "rows.csv"

    write_csv(destination, [{"name": "Pump"}, {"value": "Running"}])

    with destination.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows == [
        {"name": "Pump", "value": ""},
        {"name": "", "value": "Running"},
    ]


def test_alarms_are_discovered_by_report_headers_and_not_trigger_name() -> None:
    sheets: Workbook = {
        "SyntheticSheet": [
            {"row": 1, "cells": {"G": "ALARM REPORT"}},
            {
                "row": 2,
                "cells": {
                    "Z": "Trigger",
                    "C": "Alarm Type",
                    "M": "Edge Detection",
                    "AA": "Value",
                    "F": "Deadband Mode",
                    "R": "Deadband Level",
                    "H": "Message",
                },
            },
            {
                "row": 3,
                "cells": {
                    "Z": "MotorFault",
                    "C": "Bit",
                    "M": "Equal",
                    "AA": "1",
                    "F": "Percent",
                    "R": "0",
                    "H": "Synthetic motor fault",
                },
            },
            {"row": 4, "cells": {"B": "Alarms Additional Settings"}},
        ]
    }

    assert alarms(sheets) == [
        {
            "trigger": "MotorFault",
            "alarm_type": "Bit",
            "edge_detection": "Equal",
            "value": "1",
            "deadband_mode": "Percent",
            "deadband_level": "0",
            "message": "Synthetic motor fault",
            "source_row": "3",
        }
    ]


def test_clean_room_workbook_exercises_the_complete_report(tmp_path) -> None:
    workbook = tmp_path / "synthetic.xlsx"
    build_synthetic_ccw_workbook(workbook)

    report = build_report(workbook)

    assert report["application"] == {
        "name": "TwinForgeSyntheticFixture",
        "target": "2711R-T7T",
        "version": "8.012",
    }
    assert report["summary"] == {
        "external_tag_count": 5,
        "tag_types": {"Boolean": 3, "16 bit integer": 2},
        "screen_count": 1,
        "screen_object_count": 6,
        "alarm_count": 1,
    }
    assert report["communications"]["controllers"][0]["address"] == "192.0.2.10"
    assert report["diagnostics"] == {
        "worksheet_count": 7,
        "worksheet_names": [f"Sheet{index}" for index in range(1, 8)],
        "recognized_report_sections": [
            "ALARM REPORT",
            "COMMUNICATION REPORT",
            "SCREEN REPORT",
            "TAG REPORT",
        ],
        "unrecognized_report_sections": [],
        "warnings": [],
    }
    assert [tag["name"] for tag in report["tags"]] == [
        "StartCommand",
        "MotorRunning",
        "SpeedSetpoint",
        "MotorSpeed",
        "MotorFault",
    ]
    assert report["alarms"][0]["trigger"] == "MotorFault"


def test_report_sections_survive_worksheet_renaming_and_reordering(tmp_path) -> None:
    conventional = tmp_path / "conventional.xlsx"
    semantic = tmp_path / "semantic.xlsx"
    build_synthetic_ccw_workbook(conventional)
    build_synthetic_ccw_workbook(semantic, semantic_sheet_names=True)

    conventional_report = build_report(conventional)
    semantic_report = build_report(semantic)

    for field in (
        "application",
        "summary",
        "communications",
        "tags",
        "screens",
        "screen_objects",
        "alarms",
    ):
        assert semantic_report[field] == conventional_report[field]
    assert semantic_report["diagnostics"]["worksheet_names"] == [
        "NetworkConfiguration",
        "AlarmConfiguration",
        "DisplayDefinitions",
        "UnusedOne",
        "TagDefinitions",
        "UnusedTwo",
        "UnusedThree",
    ]


def test_non_xlsx_input_has_a_clear_domain_error(tmp_path) -> None:
    source = tmp_path / "not-a-workbook.xlsx"
    source.write_text("not a ZIP package", encoding="utf-8")

    with pytest.raises(WorkbookReadError, match="not a valid XLSX ZIP package"):
        read_workbook(source)


def test_cli_reports_malformed_workbook_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "not-a-workbook.xlsx"
    source.write_text("not a ZIP package", encoding="utf-8")

    with pytest.raises(SystemExit) as captured:
        main([str(source), "--output", str(tmp_path / "output")])

    stderr = capsys.readouterr().err
    assert captured.value.code == 2
    assert "not a valid XLSX ZIP package" in stderr
    assert "Traceback" not in stderr


def test_missing_required_ccw_sections_are_reported() -> None:
    sheets: Workbook = {"Sheet1": [{"row": 6, "cells": {"A": "TAG REPORT"}}]}

    with pytest.raises(UnsupportedWorkbookError) as captured:
        validate_workbook(sheets)

    message = str(captured.value)
    assert "COMMUNICATION REPORT" in message
    assert "SCREEN REPORT" in message


def test_unknown_report_sections_are_preserved_as_diagnostics() -> None:
    sheets: Workbook = {
        "Sheet1": [
            {
                "row": 6,
                "cells": {
                    "A": "TAG REPORT",
                    "B": "SCREEN REPORT",
                    "C": "COMMUNICATION REPORT",
                    "D": "FUTURE REPORT",
                },
            }
        ]
    }

    diagnostics = validate_workbook(sheets)

    assert diagnostics["unrecognized_report_sections"] == ["FUTURE REPORT"]
    assert diagnostics["warnings"] == [
        "unrecognized report section preserved as raw evidence: FUTURE REPORT"
    ]
