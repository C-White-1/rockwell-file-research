"""Locate CCW report sections by semantic heading."""

from rockwell_file_research.ccw.types import Workbook, WorksheetRow


def section_rows(sheets: Workbook, title: str) -> list[WorksheetRow]:
    """Return the worksheet containing an exact top-level report heading."""

    for rows in sheets.values():
        if any(title in row["cells"].values() for row in rows):
            return rows
    return []
