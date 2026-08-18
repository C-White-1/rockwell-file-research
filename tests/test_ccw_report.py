"""Synthetic unit tests for the CCW report parser helpers."""

import csv

from rockwell_file_research.ccw.export import write_csv
from rockwell_file_research.ccw.normalize import alarms
from rockwell_file_research.ccw.reporting import build_report
from rockwell_file_research.ccw.types import Workbook
from rockwell_file_research.ccw.xlsx import column_name
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
                    "B": "Trigger",
                    "C": "Alarm Type",
                    "E": "Edge Detection",
                    "Q": "Message",
                },
            },
            {
                "row": 3,
                "cells": {
                    "B": "MotorFault",
                    "C": "Bit",
                    "E": "Equal",
                    "G": "1",
                    "J": "Percent",
                    "N": "0",
                    "Q": "Synthetic motor fault",
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
    assert [tag["name"] for tag in report["tags"]] == [
        "StartCommand",
        "MotorRunning",
        "SpeedSetpoint",
        "MotorSpeed",
        "MotorFault",
    ]
    assert report["alarms"][0]["trigger"] == "MotorFault"
