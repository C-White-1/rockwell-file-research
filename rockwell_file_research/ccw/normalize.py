"""Normalize known CCW worksheet sections while retaining raw evidence."""

from __future__ import annotations

from rockwell_file_research.ccw.contracts import (
    ALARM_HEADERS,
    CONTROLLER_HEADERS,
    SCREEN_LIST_HEADERS,
    SCREEN_OBJECT_HEADERS,
    TAG_HEADERS,
)
from rockwell_file_research.ccw.models import (
    AlarmRecord,
    ApplicationIdentity,
    Communications,
    ControllerRecord,
    ScreenObjectRecord,
    ScreenRecord,
    TagRecord,
)
from rockwell_file_research.ccw.sections import section_rows
from rockwell_file_research.ccw.tables import (
    compound_headers,
    find_header,
    rows_until,
    setting_value,
    value,
    values_between,
)
from rockwell_file_research.ccw.types import Workbook


def application(sheets: Workbook) -> ApplicationIdentity:
    """Extract application identity from the main report worksheet."""

    rows = section_rows(sheets, "TAG REPORT")
    report_index = next(
        (
            index
            for index, row in enumerate(rows)
            if "TAG REPORT" in row["cells"].values()
        ),
        len(rows),
    )
    preamble = rows[:report_index]
    header = next(
        (
            row["cells"]
            for row in preamble
            if any(value.startswith("2711") for value in row["cells"].values())
        ),
        {},
    )
    target = next((value for value in header.values() if value.startswith("2711")), "")
    version = next(
        (
            value.lstrip(", ")
            for value in header.values()
            if value.strip().startswith(",")
        ),
        "",
    )
    name = next(
        (
            value
            for row in preamble
            for value in row["cells"].values()
            if value not in header.values()
        ),
        "",
    )
    return {"name": name, "target": target, "version": version}


def tags(sheets: Workbook) -> list[TagRecord]:
    """Extract known external-tag fields."""

    result: list[TagRecord] = []
    data_types = {"Boolean", "16 bit integer", "Real", "String"}
    rows = section_rows(sheets, "TAG REPORT")
    found = find_header(
        rows,
        set(TAG_HEADERS),
    )
    if found is None:
        return result
    header_index, columns = found
    data_start = header_index + 1
    if data_start < len(rows) and {"Min", "Max"}.intersection(
        rows[data_start]["cells"].values()
    ):
        columns = compound_headers(
            rows[header_index]["cells"], rows[data_start]["cells"]
        )
        data_start += 1

    for row in rows_until(rows, data_start, {"Memory Tags"}):
        cells = row["cells"]
        data_type = value(cells, columns, "Data Type")
        if data_type not in data_types:
            continue
        result.append(
            {
                "name": value(cells, columns, "Name"),
                "data_type": data_type,
                "address": value(cells, columns, "Address"),
                "controller": value(cells, columns, "Controller"),
                "description": value(cells, columns, "Description"),
                "entry_min": value(cells, columns, "Data Entry Min"),
                "entry_max": value(cells, columns, "Data Entry Max"),
                "access": value(cells, columns, "Access"),
                "update_rate_ms": value(cells, columns, "Update Rate"),
                "scaling_enabled": value(cells, columns, "Scaling"),
                "raw_min": value(cells, columns, "Raw Min"),
                "raw_max": value(cells, columns, "Raw Max"),
                "scaled_min": value(cells, columns, "Scaled Min"),
                "scaled_max": value(cells, columns, "Scaled Max"),
                "source_row": str(row["row"]),
            }
        )
    return result


def screens(
    sheets: Workbook,
) -> tuple[list[ScreenRecord], list[ScreenObjectRecord]]:
    """Extract screen inventory and screen-object bindings."""

    screen_rows: list[ScreenRecord] = []
    objects: list[ScreenObjectRecord] = []
    rows = section_rows(sheets, "SCREEN REPORT")
    list_header = find_header(rows, set(SCREEN_LIST_HEADERS))
    if list_header is not None:
        index, columns = list_header
        for row in rows_until(rows, index + 1, {"Screen Shots"}):
            cells = row["cells"]
            if not value(cells, columns, "Name") or not value(cells, columns, "Number"):
                continue
            screen_rows.append(
                {
                    "name": value(cells, columns, "Name"),
                    "number": value(cells, columns, "Number"),
                    "description": value(cells, columns, "Description"),
                    "rights": value(cells, columns, "Rights"),
                    "source_row": str(row["row"]),
                }
            )

    current = ""
    object_columns: dict[str, str] = {}
    for row in rows:
        cells = row["cells"]
        if "Screen:" in cells.values():
            label_column = next(
                column for column, item in cells.items() if item == "Screen:"
            )
            following = values_between(cells, label_column, "ZZ")
            current = following[0] if following else ""
            continue
        labels = {item: column for column, item in cells.items()}
        required = set(SCREEN_OBJECT_HEADERS)
        if required <= labels.keys():
            object_columns = labels
            continue
        if current and object_columns:
            name = value(cells, object_columns, "Object Name")
            position = value(cells, object_columns, "Position")
            size = value(cells, object_columns, "Size")
            if not name or not position or not size:
                continue
            tag_values = values_between(
                cells,
                object_columns["Tag"],
                object_columns["Position"],
            )
            objects.append(
                {
                    "screen": current,
                    "name": name,
                    "tag_1": value(cells, object_columns, "Tag"),
                    "tag_2": tag_values[0] if tag_values else "",
                    "tag_3": tag_values[1] if len(tag_values) > 1 else "",
                    "position": position,
                    "size": size,
                    "touchscreen": value(cells, object_columns, "Touchscreen"),
                    "accept_focus": value(cells, object_columns, "Accept Focus"),
                    "function_key": value(cells, object_columns, "Function Key"),
                    "source_row": str(row["row"]),
                }
            )
    return screen_rows, objects


def alarms(sheets: Workbook) -> list[AlarmRecord]:
    """Extract basic alarms by report headings rather than trigger naming."""

    result: list[AlarmRecord] = []
    rows = section_rows(sheets, "ALARM REPORT")
    found = find_header(rows, set(ALARM_HEADERS))
    if found is None:
        return result
    index, columns = found
    for row in rows_until(rows, index + 1, {"Alarms Additional Settings"}):
        cells = row["cells"]
        if not value(cells, columns, "Trigger") or not value(
            cells, columns, "Alarm Type"
        ):
            continue
        result.append(
            {
                "trigger": value(cells, columns, "Trigger"),
                "alarm_type": value(cells, columns, "Alarm Type"),
                "edge_detection": value(cells, columns, "Edge Detection"),
                "value": value(cells, columns, "Value"),
                "deadband_mode": value(cells, columns, "Deadband Mode"),
                "deadband_level": value(cells, columns, "Deadband Level"),
                "message": value(cells, columns, "Message"),
                "source_row": str(row["row"]),
            }
        )
    return result


def communications(sheets: Workbook) -> Communications:
    """Extract protocol and configured controller evidence."""

    rows = section_rows(sheets, "COMMUNICATION REPORT")
    controllers: list[ControllerRecord] = []
    found = find_header(rows, set(CONTROLLER_HEADERS))
    if found is not None:
        index, columns = found
    else:
        index, columns = len(rows), {}
    for row in rows[index + 1 :]:
        cells = row["cells"]
        if not value(cells, columns, "Name") or not value(
            cells, columns, "Controller Type"
        ):
            continue
        controllers.append(
            {
                "name": value(cells, columns, "Name"),
                "controller_type": value(cells, columns, "Controller Type"),
                "address": value(cells, columns, "Address"),
                "description": value(cells, columns, "Description"),
                "response_timeout_ms": value(
                    cells, columns, "Response Timeout Milliseconds"
                ),
                "fail_after": value(cells, columns, "Fail After"),
                "connection_timeout_s": value(
                    cells, columns, "Connection Timeout Seconds"
                ),
                "inter_request_delay_ms": value(
                    cells, columns, "Inter Request Delay Milliseconds"
                ),
                "source_row": str(row["row"]),
            }
        )
    return {
        "protocol": setting_value(rows, "Protocol :"),
        "connection_type": setting_value(rows, "Connection Type :"),
        "controllers": controllers,
    }
