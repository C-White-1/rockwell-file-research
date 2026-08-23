"""Tests for privacy-aware probable instruction access CSV output."""

import csv
import io
from typing import Any, cast

from rockwell_file_research.rss.candidate_access_csv import (
    render_instruction_candidate_access_csv,
)
from rockwell_file_research.rss.models import RSSInventory


def _inventory(*, include_text: bool) -> RSSInventory:
    operand_hash = "a" * 64
    program_hash = "b" * 64
    return cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": [
                        {
                            "proposed_mnemonic": "XIC",
                            "selector": 0x39,
                            "selector_offset": 120,
                            "confidence": "probable",
                            "evidence_profile": "synthetic/ml1400/v1",
                            "operands": [
                                {
                                    "role": "condition",
                                    "access": "read",
                                    "address_family": "input",
                                    "offset": 112,
                                    "length": 5,
                                    "sha256": operand_hash,
                                    "value": "I:0/0" if include_text else None,
                                }
                            ],
                            "diagnostics": ["Synthetic candidate evidence."],
                            "program_file_number": 2,
                            "program_file_name_sha256": program_hash,
                            "program_file_name": "MAIN" if include_text else None,
                            "rung_index": 4,
                            "rung_start_offset": 100,
                            "rung_end_offset": 140,
                        }
                    ]
                }
            },
        ),
    )


def test_candidate_access_csv_preserves_rung_and_access_evidence() -> None:
    rows = list(
        csv.DictReader(
            io.StringIO(
                render_instruction_candidate_access_csv(_inventory(include_text=True))
            )
        )
    )

    assert rows == [
        {
            "proposed_mnemonic": "XIC",
            "confidence": "probable",
            "access": "read",
            "role": "condition",
            "address_family": "input",
            "operand": "I:0/0",
            "operand_sha256": "a" * 64,
            "program_file_number": "2",
            "program_file_name": "MAIN",
            "program_file_name_sha256": "b" * 64,
            "rung_index": "4",
            "rung_start_offset": "100",
            "rung_end_offset": "140",
            "selector_hex": "0x39",
            "selector_offset": "120",
            "evidence_profile": "synthetic/ml1400/v1",
            "diagnostics": "Synthetic candidate evidence.",
        }
    ]


def test_candidate_access_csv_redacts_text_but_keeps_hashes() -> None:
    row = next(
        csv.DictReader(
            io.StringIO(
                render_instruction_candidate_access_csv(_inventory(include_text=False))
            )
        )
    )

    assert row["operand"] == ""
    assert row["program_file_name"] == ""
    assert row["operand_sha256"] == "a" * 64
    assert row["program_file_name_sha256"] == "b" * 64
