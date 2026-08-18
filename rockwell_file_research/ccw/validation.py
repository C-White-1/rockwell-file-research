"""Validate CCW report signatures and describe recognized content."""

from __future__ import annotations

from typing import Any

from rockwell_file_research.ccw.errors import UnsupportedWorkbookError
from rockwell_file_research.ccw.types import Workbook

REQUIRED_REPORTS = {"TAG REPORT", "SCREEN REPORT", "COMMUNICATION REPORT"}
KNOWN_REPORTS = REQUIRED_REPORTS | {
    "ALARM REPORT",
    "EMAIL REPORT",
    "FTP REPORT",
    "LANGUAGE REPORT",
    "RECIPE REPORT",
    "SECURITY REPORT",
    "SETTINGS REPORT",
}


def report_titles(sheets: Workbook) -> set[str]:
    """Return top-level uppercase report headings found in any worksheet."""

    return {
        value
        for rows in sheets.values()
        for row in rows
        for value in row["cells"].values()
        if value.endswith(" REPORT") and value.isupper()
    }


def validate_workbook(sheets: Workbook) -> dict[str, Any]:
    """Reject unsupported layouts and return non-destructive diagnostics."""

    titles = report_titles(sheets)
    missing = sorted(REQUIRED_REPORTS - titles)
    if missing:
        missing_text = ", ".join(missing)
        raise UnsupportedWorkbookError(
            f"workbook is not a supported CCW PanelView report; "
            f"missing required sections: {missing_text}"
        )

    unknown = sorted(titles - KNOWN_REPORTS)
    warnings = [
        f"unrecognized report section preserved as raw evidence: {title}"
        for title in unknown
    ]
    return {
        "worksheet_count": len(sheets),
        "worksheet_names": list(sheets),
        "recognized_report_sections": sorted(titles & KNOWN_REPORTS),
        "unrecognized_report_sections": unknown,
        "warnings": warnings,
    }
