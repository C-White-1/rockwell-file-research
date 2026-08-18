"""Normalize known CCW worksheet sections while retaining raw evidence."""

from __future__ import annotations

from typing import Any

from rockwell_file_research.ccw.sections import section_rows
from rockwell_file_research.ccw.types import Workbook


def application(sheets: Workbook) -> dict[str, str]:
    """Extract application identity from the main report worksheet."""

    rows = section_rows(sheets, "TAG REPORT")
    title = next((row["cells"] for row in rows if row["row"] == 2), {})
    name = next(iter(title.values()), "")
    header = next((row["cells"] for row in rows if row["row"] == 3), {})
    target = next((value for value in header.values() if value.startswith("2711")), "")
    version = next(
        (
            value.lstrip(", ")
            for value in header.values()
            if value.strip().startswith(",")
        ),
        "",
    )
    return {"name": name, "target": target, "version": version}


def tags(sheets: Workbook) -> list[dict[str, str]]:
    """Extract known external-tag fields."""

    result: list[dict[str, str]] = []
    data_types = {"Boolean", "16 bit integer", "Real", "String"}
    for row in section_rows(sheets, "TAG REPORT"):
        cells = row["cells"]
        if cells.get("C") not in data_types or cells.get("B") == "Name":
            continue
        result.append(
            {
                "name": cells.get("B", ""),
                "data_type": cells.get("C", ""),
                "address": cells.get("E", ""),
                "controller": cells.get("G", ""),
                "description": cells.get("I", ""),
                "entry_min": cells.get("L", ""),
                "entry_max": cells.get("O", ""),
                "access": cells.get("Q", ""),
                "update_rate_ms": cells.get("S", ""),
                "scaling_enabled": cells.get("T", ""),
                "raw_min": cells.get("V", ""),
                "raw_max": cells.get("W", ""),
                "scaled_min": cells.get("X", ""),
                "scaled_max": cells.get("Y", ""),
                "source_row": str(row["row"]),
            }
        )
    return result


def screens(
    sheets: Workbook,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Extract screen inventory and screen-object bindings."""

    screen_rows: list[dict[str, str]] = []
    objects: list[dict[str, str]] = []
    in_list = False
    current = ""
    for row in section_rows(sheets, "SCREEN REPORT"):
        cells = row["cells"]
        if cells.get("B") == "Name" and cells.get("G") == "Number":
            in_list = True
            continue
        if cells.get("B") == "Screen Shots":
            in_list = False
        if in_list and cells.get("B") and cells.get("G"):
            screen_rows.append(
                {
                    "name": cells["B"],
                    "number": cells["G"],
                    "description": cells.get("L", ""),
                    "rights": cells.get("U", ""),
                    "source_row": str(row["row"]),
                }
            )
        if cells.get("B") == "Screen:":
            current = cells.get("C", "")
            continue
        if (
            current
            and cells.get("B")
            and cells.get("B") != "Object Name"
            and cells.get("N")
            and cells.get("R")
        ):
            objects.append(
                {
                    "screen": current,
                    "name": cells.get("B", ""),
                    "tag_1": cells.get("E", ""),
                    "tag_2": cells.get("H", ""),
                    "tag_3": cells.get("K", ""),
                    "position": cells.get("N", ""),
                    "size": cells.get("R", ""),
                    "touchscreen": cells.get("W", ""),
                    "accept_focus": cells.get("Y", ""),
                    "function_key": cells.get("AB", ""),
                    "source_row": str(row["row"]),
                }
            )
    return screen_rows, objects


def alarms(sheets: Workbook) -> list[dict[str, str]]:
    """Extract basic alarms by report headings rather than trigger naming."""

    result: list[dict[str, str]] = []
    in_basic_settings = False
    for row in section_rows(sheets, "ALARM REPORT"):
        cells = row["cells"]
        if cells.get("B") == "Trigger" and cells.get("C") == "Alarm Type":
            in_basic_settings = True
            continue
        if cells.get("B") == "Alarms Additional Settings":
            break
        if not in_basic_settings or not cells.get("B") or not cells.get("C"):
            continue
        result.append(
            {
                "trigger": cells.get("B", ""),
                "alarm_type": cells.get("C", ""),
                "edge_detection": cells.get("E", ""),
                "value": cells.get("G", ""),
                "deadband_mode": cells.get("J", ""),
                "deadband_level": cells.get("N", ""),
                "message": cells.get("Q", ""),
                "source_row": str(row["row"]),
            }
        )
    return result


def communications(sheets: Workbook) -> dict[str, Any]:
    """Extract protocol and configured controller evidence."""

    rows = section_rows(sheets, "COMMUNICATION REPORT")
    by_row = {row["row"]: row["cells"] for row in rows}
    controllers: list[dict[str, str]] = []
    for row in rows:
        cells = row["cells"]
        if cells.get("B") in (None, "Name") or not cells.get("C"):
            continue
        if row["row"] > 16:
            controllers.append(
                {
                    "name": cells.get("B", ""),
                    "controller_type": cells.get("C", ""),
                    "address": cells.get("F", ""),
                    "description": cells.get("H", ""),
                    "response_timeout_ms": cells.get("L", ""),
                    "fail_after": cells.get("P", ""),
                    "connection_timeout_s": cells.get("R", ""),
                    "inter_request_delay_ms": cells.get("T", ""),
                    "source_row": str(row["row"]),
                }
            )
    return {
        "protocol": by_row.get(8, {}).get("D", ""),
        "connection_type": by_row.get(10, {}).get("D", ""),
        "controllers": controllers,
    }
