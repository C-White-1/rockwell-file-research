"""Render privacy-aware decoded RSS data-file values as CSV."""

from __future__ import annotations

import csv
import io
from typing import cast

from rockwell_file_research.rss.models import RSSInventory

FIELDNAMES = [
    "section",
    "data_type",
    "file_number",
    "element_index",
    "address",
    "decimal_value",
    "hex_value",
    "array_element_count",
    "array_sha256",
    "header_offset",
    "values_offset",
    "private_values_included",
]


def render_data_value_csv(inventory: RSSInventory) -> str:
    """Render deterministic rows while preserving inventory redaction."""

    rows: list[dict[str, object]] = []
    for section in inventory["data_file_sections"]:
        for array in section["integer_value_arrays"]:
            values = array["values"]
            for index in range(array["element_count"]):
                value = values[index] if values is not None else None
                rows.append(
                    {
                        "section": section["name"],
                        "data_type": "integer",
                        "file_number": array["file_number"],
                        "element_index": index,
                        "address": f"N{array['file_number']}:{index}",
                        "decimal_value": "" if value is None else value,
                        "hex_value": "" if value is None else f"{value & 0xFFFF:04X}",
                        "array_element_count": array["element_count"],
                        "array_sha256": array["values_sha256"],
                        "header_offset": array["header_offset"],
                        "values_offset": array["values_offset"],
                        "private_values_included": section["private_values_included"],
                    }
                )
        for array in section["binary_word_arrays"]:
            words = array["words"]
            for index in range(array["element_count"]):
                value = words[index] if words is not None else None
                rows.append(
                    {
                        "section": section["name"],
                        "data_type": "binary_word",
                        "file_number": array["file_number"],
                        "element_index": index,
                        "address": f"B{array['file_number']}:{index}",
                        "decimal_value": "" if value is None else value,
                        "hex_value": "" if value is None else f"{value:04X}",
                        "array_element_count": array["element_count"],
                        "array_sha256": array["values_sha256"],
                        "header_offset": array["header_offset"],
                        "values_offset": array["values_offset"],
                        "private_values_included": section["private_values_included"],
                    }
                )

    rows.sort(
        key=lambda row: (
            str(row["section"]),
            str(row["data_type"]),
            cast(int, row["file_number"]),
            cast(int, row["element_index"]),
        )
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()
