"""Reusable table and label discovery over retained worksheet cells."""

from __future__ import annotations

from collections.abc import Iterable

from rockwell_file_research.ccw.types import WorksheetRow


def find_header(
    rows: list[WorksheetRow],
    required_labels: set[str],
    *,
    start: int = 0,
) -> tuple[int, dict[str, str]] | None:
    """Find a row containing all labels and map each label to its column."""

    for index in range(start, len(rows)):
        by_label = {value: column for column, value in rows[index]["cells"].items()}
        if required_labels <= by_label.keys():
            return index, by_label
    return None


def value(cells: dict[str, str], columns: dict[str, str], label: str) -> str:
    """Read the value under a discovered header label."""

    column = columns.get(label)
    return cells.get(column, "") if column is not None else ""


def rows_until(
    rows: list[WorksheetRow],
    start: int,
    stop_values: set[str],
) -> Iterable[WorksheetRow]:
    """Yield rows until a cell exactly matches a semantic stop marker."""

    for row in rows[start:]:
        if stop_values.intersection(row["cells"].values()):
            break
        yield row


def setting_value(rows: list[WorksheetRow], label: str) -> str:
    """Return the first other cell on the row containing a setting label."""

    for row in rows:
        cells = row["cells"]
        if label not in cells.values():
            continue
        return next((item for item in cells.values() if item != label), "")
    return ""


def column_number(column: str) -> int:
    """Convert an Excel column name to a one-based numeric position."""

    result = 0
    for character in column:
        result = result * 26 + ord(character) - ord("A") + 1
    return result


def compound_headers(
    primary: dict[str, str],
    secondary: dict[str, str],
) -> dict[str, str]:
    """Combine merged-style primary headings with their secondary labels."""

    parents = sorted(
        ((column_number(column), label) for column, label in primary.items()),
        key=lambda item: item[0],
    )
    result = {label: column for column, label in primary.items()}
    for column, child in secondary.items():
        position = column_number(column)
        parent = next(
            label
            for parent_position, label in reversed(parents)
            if parent_position <= position
        )
        result[f"{parent} {child}"] = column
    return result


def values_between(
    cells: dict[str, str],
    start_column: str,
    end_column: str,
) -> list[str]:
    """Return values in columns strictly between two discovered headings."""

    start = column_number(start_column)
    end = column_number(end_column)
    return [
        item
        for column, item in sorted(
            cells.items(), key=lambda pair: column_number(pair[0])
        )
        if start < column_number(column) < end
    ]
