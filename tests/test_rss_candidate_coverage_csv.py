"""Tests for conservative rung-level candidate coverage."""

import csv
import io
from typing import Any, cast

from rockwell_file_research.rss.candidate_coverage_csv import (
    render_candidate_coverage_csv,
)
from rockwell_file_research.rss.models import RSSInventory


def test_candidate_coverage_reports_attributed_and_unattributed_operands() -> None:
    candidate = {
        "proposed_mnemonic": "XIC",
        "selector": 0x39,
        "selector_offset": 30,
        "confidence": "probable",
        "evidence_profile": "synthetic",
        "operands": [
            {
                "role": "condition",
                "access": "read",
                "address_family": "binary",
                "offset": 20,
                "length": 6,
                "sha256": "a" * 64,
                "value": "B3:0/0",
            }
        ],
        "diagnostics": [],
        "program_file_number": 2,
        "program_file_name_sha256": "b" * 64,
        "program_file_name": "MAIN",
        "rung_index": 0,
        "rung_start_offset": 10,
        "rung_end_offset": 80,
    }
    operands = [
        {
            "offset": offset,
            "length": 6,
            "sha256": str(offset) * 32,
            "indirect": False,
            "operand": value,
            "program_file_number": 2,
            "program_file_name_sha256": "b" * 64,
            "program_file_name": "MAIN",
            "rung_index": rung,
            "rung_start_offset": 10 + rung * 100,
            "rung_end_offset": 80 + rung * 100,
        }
        for offset, value, rung in (
            (20, "B3:0/0", 0),
            (40, "B3:0/1", 0),
            (120, "B3:1/0", 1),
        )
    ]
    rungs = [
        {
            "program_file_number": 2,
            "program_file_name_sha256": "b" * 64,
            "program_file_name": "MAIN",
            "rung_index": rung,
        }
        for rung in (0, 1)
    ]
    inventory = cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": [candidate],
                    "operands": operands,
                    "rung_records": rungs,
                }
            },
        ),
    )

    rows = list(csv.DictReader(io.StringIO(render_candidate_coverage_csv(inventory))))

    assert rows[0]["recovered_operand_count"] == "2"
    assert rows[0]["attributed_operand_count"] == "1"
    assert rows[0]["unattributed_operand_count"] == "1"
    assert rows[0]["operand_attribution_status"] == "partially_attributed"
    assert rows[1]["candidate_instruction_count"] == "0"
    assert rows[1]["operand_attribution_status"] == "none_attributed"
