"""Validate CCW report signatures and describe recognized content."""

from __future__ import annotations

from typing import Any

from rockwell_file_research.ccw.contracts import SECTION_CONTRACTS, SectionContract
from rockwell_file_research.ccw.errors import UnsupportedWorkbookError
from rockwell_file_research.ccw.sections import section_rows
from rockwell_file_research.ccw.tables import find_header
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

    contract_results = [
        _assess_contract(sheets, contract) for contract in SECTION_CONTRACTS
    ]
    required_failures = [
        result
        for result in contract_results
        if result["required"] and result["status"] != "supported"
    ]
    if required_failures:
        details = "; ".join(
            _contract_failure_text(result) for result in required_failures
        )
        raise UnsupportedWorkbookError(
            f"CCW report sections do not match the supported semantic schema: {details}"
        )

    unknown = sorted(titles - KNOWN_REPORTS)
    warnings = [
        f"unrecognized report section preserved as raw evidence: {title}"
        for title in unknown
    ]
    warnings.extend(
        _contract_failure_text(result)
        for result in contract_results
        if not result["required"] and result["status"] == "unsupported"
    )
    return {
        "worksheet_count": len(sheets),
        "worksheet_names": list(sheets),
        "recognized_report_sections": sorted(titles & KNOWN_REPORTS),
        "unrecognized_report_sections": unknown,
        "section_contracts": contract_results,
        "warnings": warnings,
    }


def _assess_contract(
    sheets: Workbook,
    contract: SectionContract,
) -> dict[str, Any]:
    rows = section_rows(sheets, contract.title)
    if not rows:
        return {
            "section": contract.title,
            "required": contract.required,
            "status": "absent",
            "missing_table_headers": [],
            "missing_setting_labels": [],
        }

    missing_tables = [
        sorted(headers)
        for headers in contract.table_headers
        if find_header(rows, set(headers)) is None
    ]
    values = {item for row in rows for item in row["cells"].values()}
    missing_settings = sorted(contract.setting_labels - values)
    status = (
        "supported" if not missing_tables and not missing_settings else "unsupported"
    )
    return {
        "section": contract.title,
        "required": contract.required,
        "status": status,
        "missing_table_headers": missing_tables,
        "missing_setting_labels": missing_settings,
    }


def _contract_failure_text(result: dict[str, Any]) -> str:
    details: list[str] = []
    missing_tables = result["missing_table_headers"]
    if missing_tables:
        details.append(
            "missing table headers "
            + ", ".join("/".join(headers) for headers in missing_tables)
        )
    missing_settings = result["missing_setting_labels"]
    if missing_settings:
        details.append("missing settings " + ", ".join(missing_settings))
    suffix = "; ".join(details) if details else f"status {result['status']}"
    return f"{result['section']}: {suffix}"
