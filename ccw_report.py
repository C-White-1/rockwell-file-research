"""Extract structured evidence from a CCW PanelView Excel report.

The CCW workbook remains the source of truth.  Normalized inventories are
convenience views; every non-empty workbook cell is also retained under
``raw_sheets`` so unsupported report sections are not silently discarded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": SHEET_NS, "r": REL_NS}


def _column(reference: str) -> str:
    match = re.match(r"[A-Z]+", reference)
    if match is None:
        raise ValueError(f"invalid Excel cell reference: {reference}")
    return match.group()


def read_workbook(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Read non-empty cells from every worksheet in an XLSX workbook."""

    sheets: dict[str, list[dict[str, Any]]] = {}
    with ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = [
                "".join(node.text or "" for node in item.findall(".//m:t", NS))
                for item in root.findall("m:si", NS)
            ]

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            element.attrib["Id"]: element.attrib["Target"] for element in relationships
        }

        for sheet in workbook.findall(".//m:sheet", NS):
            relation_id = sheet.attrib[f"{{{REL_NS}}}id"]
            target = targets[relation_id].lstrip("/")
            member = target if target.startswith("xl/") else f"xl/{target}"
            worksheet = ET.fromstring(archive.read(member))
            rows: list[dict[str, Any]] = []

            for row in worksheet.findall(".//m:sheetData/m:row", NS):
                cells: dict[str, str] = {}
                for cell in row.findall("m:c", NS):
                    kind = cell.attrib.get("t")
                    value_node = cell.find("m:v", NS)
                    inline_node = cell.find("m:is", NS)
                    value = ""
                    if kind == "s" and value_node is not None:
                        value = shared[int(value_node.text or "0")]
                    elif kind == "inlineStr" and inline_node is not None:
                        value = "".join(
                            node.text or ""
                            for node in inline_node.findall(".//m:t", NS)
                        )
                    elif value_node is not None:
                        value = value_node.text or ""
                    if value:
                        cells[_column(cell.attrib["r"])] = value

                if cells:
                    rows.append({"row": int(row.attrib["r"]), "cells": cells})

            sheets[sheet.attrib["name"]] = rows
    return sheets


def _sheet(sheets: dict[str, list[dict[str, Any]]], name: str) -> list[dict[str, Any]]:
    return sheets.get(name, [])


def _application(sheets: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    rows = _sheet(sheets, "Sheet1")
    title = next((row["cells"] for row in rows if row["row"] == 2), {})
    name = next(iter(title.values()), "")
    header = next((row["cells"] for row in rows if row["row"] == 3), {})
    target = next(
        (value for value in header.values() if value.startswith("2711")),
        "",
    )
    version = next(
        (
            value.lstrip(", ")
            for value in header.values()
            if value.strip().startswith(",")
        ),
        "",
    )
    return {"name": name, "target": target, "version": version}


def _tags(sheets: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    result = []
    data_types = {"Boolean", "16 bit integer", "Real", "String"}
    for row in _sheet(sheets, "Sheet1"):
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


def _screens(
    sheets: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    screens: list[dict[str, str]] = []
    objects: list[dict[str, str]] = []
    in_list = False
    current = ""

    for row in _sheet(sheets, "Sheet2"):
        cells = row["cells"]
        if cells.get("B") == "Name" and cells.get("G") == "Number":
            in_list = True
            continue
        if cells.get("B") == "Screen Shots":
            in_list = False
        if in_list and cells.get("B") and cells.get("G"):
            screens.append(
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
    return screens, objects


def _alarms(sheets: dict[str, list[dict[str, Any]]]) -> list[dict[str, str]]:
    result = []
    for row in _sheet(sheets, "Sheet4"):
        cells = row["cells"]
        if cells.get("C") != "Bit" or not cells.get("B", "").startswith("Alarm"):
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


def _communications(sheets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = _sheet(sheets, "Sheet7")
    by_row = {row["row"]: row["cells"] for row in rows}
    controllers = []
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


def build_report(path: Path) -> dict[str, Any]:
    """Build normalized and loss-preserving views of a CCW report."""

    sheets = read_workbook(path)
    tags = _tags(sheets)
    screens, objects = _screens(sheets)
    alarms = _alarms(sheets)
    return {
        "schema_version": "rockwell-file-research.ccw-report.v1",
        "source": {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
        "application": _application(sheets),
        "summary": {
            "external_tag_count": len(tags),
            "tag_types": dict(Counter(tag["data_type"] for tag in tags)),
            "screen_count": len(screens),
            "screen_object_count": len(objects),
            "alarm_count": len(alarms),
        },
        "communications": _communications(sheets),
        "tags": tags,
        "screens": screens,
        "screen_objects": objects,
        "alarms": alarms,
        "raw_sheets": sheets,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        if fieldnames:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def export_report(source: Path, destination: Path) -> dict[str, Any]:
    """Export JSON and CSV evidence derived from a CCW report."""

    report = build_report(source)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(destination / "tags.csv", report["tags"])
    _write_csv(destination / "screens.csv", report["screens"])
    _write_csv(destination / "screen_objects.csv", report["screen_objects"])
    _write_csv(destination / "alarms.csv", report["alarms"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract structured evidence from a CCW PanelView XLSX report."
    )
    parser.add_argument("source", type=Path, help="CCW-generated XLSX report")
    parser.add_argument("--output", type=Path, required=True, help="output directory")
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"source report does not exist: {args.source}")
    report = export_report(args.source, args.output)
    summary = report["summary"]
    print(
        f"Extracted {summary['external_tag_count']} tags, "
        f"{summary['screen_count']} screens, "
        f"{summary['screen_object_count']} objects, and "
        f"{summary['alarm_count']} alarms to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
