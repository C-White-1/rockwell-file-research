"""Tests for privacy-aware RSS data-value CSV rendering."""

import csv
import io
from typing import cast

from rockwell_file_research.rss.data_value_csv import render_data_value_csv
from rockwell_file_research.rss.models import RSSInventory


def _inventory(*, include_values: bool) -> RSSInventory:
    return cast(
        RSSInventory,
        {
            "data_file_sections": [
                {
                    "name": "DATA FILES",
                    "private_values_included": include_values,
                    "integer_value_arrays": [
                        {
                            "file_number": 11,
                            "header_offset": 100,
                            "values_offset": 108,
                            "element_count": 2,
                            "values_sha256": "i" * 64,
                            "values": [123, -2] if include_values else None,
                        }
                    ],
                    "binary_word_arrays": [
                        {
                            "file_number": 10,
                            "header_offset": 80,
                            "values_offset": 88,
                            "element_count": 2,
                            "values_sha256": "b" * 64,
                            "words": [0x00A5, 0x8112] if include_values else None,
                        }
                    ],
                }
            ]
        },
    )


def test_redacted_csv_preserves_structure_and_hashes_without_values():
    rows = list(
        csv.DictReader(
            io.StringIO(render_data_value_csv(_inventory(include_values=False)))
        )
    )

    assert [row["address"] for row in rows] == ["B10:0", "B10:1", "N11:0", "N11:1"]
    assert all(row["decimal_value"] == "" for row in rows)
    assert all(row["hex_value"] == "" for row in rows)
    assert {row["array_sha256"] for row in rows} == {"b" * 64, "i" * 64}


def test_private_csv_renders_decimal_and_16_bit_hex_values():
    rows = list(
        csv.DictReader(
            io.StringIO(render_data_value_csv(_inventory(include_values=True)))
        )
    )
    indexed = {row["address"]: row for row in rows}

    assert indexed["B10:0"]["decimal_value"] == "165"
    assert indexed["B10:0"]["hex_value"] == "00A5"
    assert indexed["B10:1"]["hex_value"] == "8112"
    assert indexed["N11:0"]["decimal_value"] == "123"
    assert indexed["N11:1"]["decimal_value"] == "-2"
    assert indexed["N11:1"]["hex_value"] == "FFFE"
