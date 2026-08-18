"""Create clean-room XLSX fixtures without copying a vendor workbook."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_TYPE_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("", SHEET_NS)
ET.register_namespace("r", OFFICE_REL_NS)


def _worksheet(rows: dict[int, dict[str, str]]) -> bytes:
    root = ET.Element(f"{{{SHEET_NS}}}worksheet")
    sheet_data = ET.SubElement(root, f"{{{SHEET_NS}}}sheetData")
    for row_number, values in sorted(rows.items()):
        row = ET.SubElement(
            sheet_data,
            f"{{{SHEET_NS}}}row",
            {"r": str(row_number)},
        )
        for column, value in values.items():
            cell = ET.SubElement(
                row,
                f"{{{SHEET_NS}}}c",
                {"r": f"{column}{row_number}", "t": "inlineStr"},
            )
            inline = ET.SubElement(cell, f"{{{SHEET_NS}}}is")
            ET.SubElement(inline, f"{{{SHEET_NS}}}t").text = value
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _workbook(sheet_count: int) -> bytes:
    root = ET.Element(f"{{{SHEET_NS}}}workbook")
    sheets = ET.SubElement(root, f"{{{SHEET_NS}}}sheets")
    for index in range(1, sheet_count + 1):
        ET.SubElement(
            sheets,
            f"{{{SHEET_NS}}}sheet",
            {
                "name": f"Sheet{index}",
                "sheetId": str(index),
                f"{{{OFFICE_REL_NS}}}id": f"rId{index}",
            },
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _workbook_relationships(sheet_count: int) -> bytes:
    root = ET.Element(f"{{{PACKAGE_REL_NS}}}Relationships")
    for index in range(1, sheet_count + 1):
        ET.SubElement(
            root,
            f"{{{PACKAGE_REL_NS}}}Relationship",
            {
                "Id": f"rId{index}",
                "Type": (
                    "http://schemas.openxmlformats.org/officeDocument/2006/"
                    "relationships/worksheet"
                ),
                "Target": f"worksheets/sheet{index}.xml",
            },
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _content_types(sheet_count: int) -> bytes:
    root = ET.Element(f"{{{CONTENT_TYPE_NS}}}Types")
    ET.SubElement(
        root,
        f"{{{CONTENT_TYPE_NS}}}Default",
        {
            "Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
        },
    )
    ET.SubElement(
        root,
        f"{{{CONTENT_TYPE_NS}}}Default",
        {"Extension": "xml", "ContentType": "application/xml"},
    )
    ET.SubElement(
        root,
        f"{{{CONTENT_TYPE_NS}}}Override",
        {
            "PartName": "/xl/workbook.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        },
    )
    for index in range(1, sheet_count + 1):
        ET.SubElement(
            root,
            f"{{{CONTENT_TYPE_NS}}}Override",
            {
                "PartName": f"/xl/worksheets/sheet{index}.xml",
                "ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
            },
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _package_relationships() -> bytes:
    root = ET.Element(f"{{{PACKAGE_REL_NS}}}Relationships")
    ET.SubElement(
        root,
        f"{{{PACKAGE_REL_NS}}}Relationship",
        {
            "Id": "rId1",
            "Type": (
                "http://schemas.openxmlformats.org/officeDocument/2006/"
                "relationships/officeDocument"
            ),
            "Target": "xl/workbook.xml",
        },
    )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _write_member(archive: ZipFile, name: str, content: bytes) -> None:
    member = ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
    member.compress_type = ZIP_DEFLATED
    archive.writestr(member, content)


def build_synthetic_ccw_workbook(destination: Path) -> None:
    """Write a deterministic, minimal workbook containing synthetic evidence."""

    tags = [
        ("StartCommand", "Boolean", "B3:0/0", "Read/Write"),
        ("MotorRunning", "Boolean", "B3:0/1", "Read"),
        ("SpeedSetpoint", "16 bit integer", "N7:0", "Read/Write"),
        ("MotorSpeed", "16 bit integer", "N7:1", "Read"),
        ("MotorFault", "Boolean", "B3:0/2", "Read"),
    ]
    sheet1: dict[int, dict[str, str]] = {
        2: {"D": "TwinForgeSyntheticFixture"},
        3: {"H": "2711R-T7T", "L": ", 8.012"},
        6: {"H": "TAG REPORT"},
        11: {"B": "Name", "C": "Data Type"},
    }
    for row_number, (name, data_type, address, access) in enumerate(tags, 12):
        sheet1[row_number] = {
            "B": name,
            "C": data_type,
            "E": address,
            "G": "SyntheticPLC",
            "Q": access,
            "S": "500",
            "T": "0",
        }

    sheet2 = {
        6: {"M": "SCREEN REPORT"},
        8: {"B": "Name", "G": "Number"},
        9: {"B": "Main", "G": "1", "L": "Synthetic motor screen"},
        11: {"B": "Screen Shots"},
        13: {"B": "Screen:", "C": "Main"},
        14: {"B": "Object Name", "N": "Position", "R": "Size"},
        15: {"B": "Title", "N": "10,10", "R": "240,30"},
        16: {
            "B": "StartButton",
            "E": "StartCommand",
            "N": "10,50",
            "R": "100,30",
            "W": "True",
        },
        17: {
            "B": "RunningIndicator",
            "E": "MotorRunning",
            "N": "120,50",
            "R": "100,30",
        },
        18: {
            "B": "SpeedEntry",
            "E": "SpeedSetpoint",
            "N": "10,90",
            "R": "100,30",
            "W": "True",
        },
        19: {
            "B": "SpeedDisplay",
            "E": "MotorSpeed",
            "N": "120,90",
            "R": "100,30",
        },
        20: {
            "B": "FaultIndicator",
            "E": "MotorFault",
            "N": "10,130",
            "R": "210,30",
        },
    }
    sheet4 = {
        6: {"G": "ALARM REPORT"},
        9: {"B": "Trigger", "C": "Alarm Type", "E": "Edge Detection", "Q": "Message"},
        10: {
            "B": "MotorFault",
            "C": "Bit",
            "E": "Equal",
            "G": "1",
            "J": "Percent",
            "N": "0",
            "Q": "Synthetic Motor Fault",
        },
        12: {"B": "Alarms Additional Settings"},
    }
    sheet7 = {
        6: {"I": "COMMUNICATION REPORT"},
        8: {"B": "Protocol :", "D": "Allen-Bradley MicroLogix"},
        10: {"B": "Connection Type :", "D": "Ethernet"},
        16: {"B": "Name", "C": "Controller Type", "F": "Address"},
        17: {
            "B": "SyntheticPLC",
            "C": "MicroLogix 1400",
            "F": "192.0.2.10",
            "L": "1000",
            "P": "3",
            "R": "3",
            "T": "0",
        },
    }
    worksheets = [sheet1, sheet2, {}, sheet4, {}, {}, sheet7]

    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(destination, "w") as archive:
        _write_member(archive, "[Content_Types].xml", _content_types(len(worksheets)))
        _write_member(archive, "_rels/.rels", _package_relationships())
        _write_member(archive, "xl/workbook.xml", _workbook(len(worksheets)))
        _write_member(
            archive,
            "xl/_rels/workbook.xml.rels",
            _workbook_relationships(len(worksheets)),
        )
        for index, rows in enumerate(worksheets, 1):
            _write_member(
                archive,
                f"xl/worksheets/sheet{index}.xml",
                _worksheet(rows),
            )
