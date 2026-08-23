"""Tests for the conservative probable-ladder Markdown view."""

from typing import Any, cast

from rockwell_file_research.rss.candidate_ladder import (
    render_probable_ladder_markdown,
)
from rockwell_file_research.rss.models import RSSInventory


def _candidate(mnemonic: str, value: str, offset: int) -> dict[str, Any]:
    return {
        "proposed_mnemonic": mnemonic,
        "selector": 0,
        "selector_offset": offset,
        "confidence": "probable",
        "evidence_profile": "synthetic",
        "operands": [
            {
                "role": "operand",
                "access": "read",
                "address_family": "binary",
                "offset": offset - 4,
                "length": len(value),
                "sha256": "a" * 64,
                "value": value,
            }
        ],
        "diagnostics": [],
        "program_file_number": 2,
        "program_file_name_sha256": "b" * 64,
        "program_file_name": "MAIN",
        "rung_index": 3,
        "rung_start_offset": 10,
        "rung_end_offset": 80,
    }


def test_probable_ladder_preserves_serialized_order_and_uncertainty() -> None:
    inventory = cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": [
                        _candidate("OTE", "O:0/0", 40),
                        _candidate("XIC", "I:0/0", 20),
                    ]
                }
            },
        ),
    )

    rendered = render_probable_ladder_markdown(inventory)

    assert "Program 2: MAIN — rung 3" in rendered
    assert "|--[?XIC I:0/0]--(?OTE O:0/0)--|" in rendered
    assert "Topology: unresolved; serialized record order only." in rendered
    assert "not reconstructed source" in rendered


def test_probable_ladder_treats_serialized_order_as_unresolved_topology() -> None:
    candidates = [
        _candidate("XIC", "B3:0/0", 20),
        _candidate("OTE", "B3:0/1", 40),
    ]
    rung = {
        "program_file_number": 2,
        "program_file_name": "MAIN",
        "program_file_name_sha256": "b" * 64,
        "rung_index": 3,
        "candidate_topology": {
            "kind": "serialized_order",
            "evidence_profile": "rslogix500/ml1400/simple-topology-candidate/v1",
            "items": [
                {"kind": "instruction", "mnemonic": "XIC", "selector_offset": 20},
                {"kind": "instruction", "mnemonic": "OTE", "selector_offset": 40},
            ],
        },
    }
    inventory = cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": candidates,
                    "rung_records": [rung],
                }
            },
        ),
    )

    rendered = render_probable_ladder_markdown(inventory)

    assert "|--[?XIC B3:0/0]--(?OTE B3:0/1)--|" in rendered
    assert "Topology: unresolved; serialized record order only." in rendered
    assert "probable candidate branch structure" not in rendered


def test_probable_ladder_renders_candidate_parallel_legs() -> None:
    candidates = [
        _candidate("XIC", "B3:0/0", 20),
        _candidate("XIC", "B3:0/1", 30),
        _candidate("XIO", "B3:0/2", 40),
        _candidate("OTE", "B3:0/3", 50),
    ]
    topology = {
        "kind": "series_parallel",
        "evidence_profile": "synthetic",
        "items": [
            {"kind": "instruction", "mnemonic": "XIC", "selector_offset": 20},
            {
                "kind": "parallel",
                "offset": 25,
                "legs": [
                    [{"kind": "instruction", "mnemonic": "XIC", "selector_offset": 30}],
                    [{"kind": "instruction", "mnemonic": "XIO", "selector_offset": 40}],
                ],
            },
            {"kind": "instruction", "mnemonic": "OTE", "selector_offset": 50},
        ],
    }
    rung = {
        "program_file_number": 2,
        "program_file_name": "MAIN",
        "program_file_name_sha256": "b" * 64,
        "rung_index": 3,
        "candidate_topology": topology,
    }
    inventory = cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": candidates,
                    "rung_records": [rung],
                }
            },
        ),
    )

    rendered = render_probable_ladder_markdown(inventory)

    assert (
        "|--[?XIC B3:0/0]--{ [?XIC B3:0/1] || [?XIO B3:0/2] }--(?OTE B3:0/3)--|"
        in rendered
    )
    assert "Topology: probable candidate branch structure." in rendered


def test_probable_ladder_prints_unknown_selector_in_hex_and_decimal() -> None:
    unknown = _candidate("UNKNOWN", "N7:0", 20)
    unknown["selector"] = 0x58
    unknown["confidence"] = "unclassified"
    inventory = cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": [unknown],
                    "rung_records": [],
                }
            },
        ),
    )

    rendered = render_probable_ladder_markdown(inventory)

    assert "[UNKNOWN 0x58 (88) N7:0]" in rendered


def test_probable_ladder_hides_serialized_metadata_fields() -> None:
    mov = _candidate("MOV", "1", 20)
    mov["selector"] = 0x1C
    mov["operands"].extend(
        [
            {
                "role": "source_format",
                "access": "metadata",
                "address_family": "other",
                "offset": 22,
                "length": 1,
                "sha256": "c" * 64,
                "value": "1",
            },
            {
                "role": "destination",
                "access": "write",
                "address_family": "integer",
                "offset": 24,
                "length": 4,
                "sha256": "d" * 64,
                "value": "N7:0",
            },
            {
                "role": "destination_format",
                "access": "metadata",
                "address_family": "other",
                "offset": 29,
                "length": 1,
                "sha256": "e" * 64,
                "value": "2",
            },
        ]
    )
    inventory = cast(
        RSSInventory,
        cast(
            Any,
            {
                "program_files": {
                    "instruction_candidates": [mov],
                    "rung_records": [],
                }
            },
        ),
    )

    rendered = render_probable_ladder_markdown(inventory)

    assert "[?MOV 1, N7:0]" in rendered
    assert "[?MOV 1, 1, N7:0, 2]" not in rendered
