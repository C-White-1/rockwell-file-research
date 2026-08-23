"""Tests for aggregate unknown-instruction selector reporting."""

import csv
import io
from typing import Any, cast

from rockwell_file_research.rss.models import RSSInventory
from rockwell_file_research.rss.unknown_candidate_csv import (
    render_unknown_candidate_csv,
)


def _candidate(selector: int, value: str, rung: int) -> dict[str, Any]:
    return {
        "proposed_mnemonic": "UNKNOWN",
        "selector": selector,
        "selector_offset": 100 + rung,
        "confidence": "unclassified",
        "evidence_profile": "synthetic/ml1400/unknown/v1",
        "operands": [
            {
                "role": "operand_1",
                "access": "unknown",
                "address_family": "timer",
                "offset": 90 + rung,
                "length": len(value),
                "sha256": "a" * 64,
                "value": value,
            }
        ],
        "diagnostics": [],
        "program_file_number": 2,
        "program_file_name_sha256": "b" * 64,
        "program_file_name": "MAIN",
        "rung_index": rung,
        "rung_start_offset": 80,
        "rung_end_offset": 140,
    }


def test_unknown_candidate_csv_aggregates_selector_evidence() -> None:
    known = _candidate(0x39, "I:0/0", 1)
    known["proposed_mnemonic"] = "XIC"
    inventory = cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": [
                        _candidate(0x58, "T4:0", 3),
                        _candidate(0x58, "T4:1", 4),
                        _candidate(0x0F, "T4:2", 5),
                        known,
                    ]
                }
            },
        ),
    )

    rows = list(csv.DictReader(io.StringIO(render_unknown_candidate_csv(inventory))))

    assert [row["selector_hex"] for row in rows] == ["0x0F", "0x58"]
    assert rows[1]["selector_decimal"] == "88"
    assert rows[1]["record_count"] == "2"
    assert rows[1]["operand_count_shapes"] == "1"
    assert rows[1]["address_families"] == "timer"
    assert rows[1]["program_file_count"] == "1"
    assert rows[1]["rung_count"] == "2"
