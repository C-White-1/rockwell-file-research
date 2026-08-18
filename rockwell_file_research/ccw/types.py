"""Shared structural types for CCW report processing."""

from typing import TypedDict


class WorksheetRow(TypedDict):
    """One non-empty worksheet row keyed by Excel column name."""

    row: int
    cells: dict[str, str]


Workbook = dict[str, list[WorksheetRow]]
