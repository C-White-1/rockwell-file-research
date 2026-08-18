"""Read cell evidence from an Office Open XML workbook."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from rockwell_file_research.ccw.types import Workbook, WorksheetRow

SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": SHEET_NS, "r": REL_NS}


def column_name(reference: str) -> str:
    """Return the column portion of an Excel cell reference."""

    match = re.match(r"[A-Z]+", reference)
    if match is None:
        raise ValueError(f"invalid Excel cell reference: {reference}")
    return match.group()


def read_workbook(path: Path) -> Workbook:
    """Read every non-empty cell without discarding unsupported worksheets."""

    sheets: Workbook = {}
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
            rows: list[WorksheetRow] = []
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
                        cells[column_name(cell.attrib["r"])] = value
                if cells:
                    rows.append({"row": int(row.attrib["r"]), "cells": cells})
            sheets[sheet.attrib["name"]] = rows
    return sheets
