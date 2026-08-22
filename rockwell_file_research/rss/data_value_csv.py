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
    "bit_index",
    "address",
    "decimal_value",
    "hex_value",
    "array_element_count",
    "array_sha256",
    "header_offset",
    "values_offset",
    "private_values_included",
]


def render_data_value_csv(
    inventory: RSSInventory, *, expand_binary_bits: bool = False
) -> str:
    """Render deterministic rows while preserving inventory redaction.

    Binary words remain the primary evidence. When requested, derived bit rows
    expose each word's 16 addressable positions without assigning tag names or
    application semantics.
    """

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
                        "bit_index": "",
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
                        "bit_index": "",
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
                if expand_binary_bits:
                    for bit_index in range(16):
                        bit_value = None if value is None else (value >> bit_index) & 1
                        rows.append(
                            {
                                "section": section["name"],
                                "data_type": "binary_bit",
                                "file_number": array["file_number"],
                                "element_index": index,
                                "bit_index": bit_index,
                                "address": (
                                    f"B{array['file_number']}:{index}/{bit_index}"
                                ),
                                "decimal_value": (
                                    "" if bit_value is None else bit_value
                                ),
                                "hex_value": "",
                                "array_element_count": array["element_count"],
                                "array_sha256": array["values_sha256"],
                                "header_offset": array["header_offset"],
                                "values_offset": array["values_offset"],
                                "private_values_included": section[
                                    "private_values_included"
                                ],
                            }
                        )

    type_order = {"binary_word": 0, "binary_bit": 1, "integer": 2}
    rows.sort(
        key=lambda row: (
            str(row["section"]),
            0 if str(row["data_type"]).startswith("binary_") else 1,
            cast(int, row["file_number"]),
            cast(int, row["element_index"]),
            type_order[str(row["data_type"])],
            -1 if row["bit_index"] == "" else cast(int, row["bit_index"]),
        )
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()
