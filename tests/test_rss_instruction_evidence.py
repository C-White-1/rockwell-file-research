"""Tests for controlled-profile RSS instruction recognition."""

import zlib

from rockwell_file_research.rss.instruction_evidence import (
    scan_controlled_instructions,
    scan_controlled_mov_instructions,
    scan_controlled_simple_bit_instructions,
)
from rockwell_file_research.rss.program_files import inspect_program_file_section


def _record(*, operand: str, selector: int) -> bytes:
    encoded = operand.encode("ascii")
    return (
        b"\x01\x00"
        + bytes([len(encoded)])
        + encoded
        + b"\x00\x00"
        + bytes([selector])
        + b"\x00\x00\x00\x00\x00\x0b\x80"
        + bytes(36)
    )


def _envelope(payload: bytes) -> bytes:
    compressed = zlib.compress(payload)
    return (
        (2).to_bytes(4, "little")
        + (16).to_bytes(4, "little")
        + len(compressed).to_bytes(4, "little")
        + len(payload).to_bytes(4, "little")
        + compressed
    )


def _mov_record(*, source: str, destination: str) -> bytes:
    source_bytes = source.encode("ascii")
    destination_bytes = destination.encode("ascii")
    return (
        b"\x04\x00"
        + bytes([len(source_bytes)])
        + source_bytes
        + b"\x01\x3f"
        + bytes([len(destination_bytes)])
        + destination_bytes
        + b"\x01\x3f\x00\x00\x1c"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def test_controlled_simple_bit_selector_family_is_recognized() -> None:
    expected = {
        0x39: "XIC",
        0x3A: "XIO",
        0x2F: "OTE",
        0x30: "OTL",
        0x31: "OTU",
    }

    for selector, mnemonic in expected.items():
        result = scan_controlled_simple_bit_instructions(
            b"prefix" + _record(operand="B3:0/1", selector=selector),
            include_private_text=True,
        )

        assert len(result) == 1
        assert result[0].mnemonic == mnemonic
        assert result[0].selector == selector
        assert result[0].operands[0].value == "B3:0/1"
        assert len(result[0].operands[0].sha256) == 64


def test_private_operand_text_is_redacted_by_default() -> None:
    result = scan_controlled_simple_bit_instructions(
        _record(operand="B3:0/1", selector=0x39)
    )

    assert result[0].operands[0].value is None
    assert len(result[0].operands[0].sha256) == 64


def test_xic_selector_is_stable_across_controlled_operand_change() -> None:
    first = scan_controlled_simple_bit_instructions(
        _record(operand="B3:0/0", selector=0x39),
        include_private_text=True,
    )[0]
    second = scan_controlled_simple_bit_instructions(
        _record(operand="B3:1/2", selector=0x39),
        include_private_text=True,
    )[0]

    assert first.mnemonic == second.mnemonic == "XIC"
    assert first.selector == second.selector == 0x39
    assert first.selector_offset == second.selector_offset
    assert first.operands[0].value == "B3:0/0"
    assert second.operands[0].value == "B3:1/2"
    assert first.operands[0].sha256 != second.operands[0].sha256


def test_unknown_selector_and_incomplete_frame_remain_uninterpreted() -> None:
    assert not scan_controlled_simple_bit_instructions(
        _record(operand="B3:0/1", selector=0x99)
    )
    assert not scan_controlled_simple_bit_instructions(
        _record(operand="B3:0/1", selector=0x39)[:-40]
    )


def test_unproven_operand_family_is_not_generalized() -> None:
    assert not scan_controlled_simple_bit_instructions(
        _record(operand="N7:0/1", selector=0x39)
    )


def test_program_file_section_exposes_controlled_instruction_evidence() -> None:
    section = inspect_program_file_section(
        _envelope(_record(operand="B3:0/1", selector=0x30)),
        include_private_text=True,
    )

    assert [
        (item.mnemonic, item.operands[0].value) for item in section.instructions
    ] == [
        ("OTL", "B3:0/1"),
    ]


def test_serial_records_preserve_source_order_by_byte_offset() -> None:
    payload = _record(operand="B3:0/0", selector=0x39) + _record(
        operand="B3:0/1", selector=0x2F
    )

    instructions = scan_controlled_simple_bit_instructions(
        payload,
        include_private_text=True,
    )

    assert [item.mnemonic for item in instructions] == ["XIC", "OTE"]
    assert [item.operands[0].value for item in instructions] == [
        "B3:0/0",
        "B3:0/1",
    ]
    assert instructions[0].selector_offset < instructions[1].selector_offset


def test_branch_framing_does_not_hide_ordered_instruction_records() -> None:
    branch_prefix = b"\xff\xff\x80\x00\x07\x00CBranch" + bytes(24)
    leg_separator = bytes(28)
    output_separator = bytes(24)
    payload = (
        branch_prefix
        + _record(operand="B3:0/1", selector=0x39)
        + leg_separator
        + _record(operand="B3:0/0", selector=0x39)
        + output_separator
        + _record(operand="B3:0/2", selector=0x2F)
    )

    instructions = scan_controlled_simple_bit_instructions(
        payload,
        include_private_text=True,
    )

    assert [item.operands[0].value for item in instructions] == [
        "B3:0/1",
        "B3:0/0",
        "B3:0/2",
    ]
    assert [item.mnemonic for item in instructions] == ["XIC", "XIC", "OTE"]


def test_controlled_mov_exposes_ordered_source_and_destination() -> None:
    result = scan_controlled_mov_instructions(
        _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )

    assert len(result) == 1
    assert result[0].mnemonic == "MOV"
    assert result[0].selector == 0x1C
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "N7:0"),
        ("destination", "N7:1"),
    ]


def test_mov_selector_is_stable_across_independent_operand_changes() -> None:
    variants = [
        _mov_record(source="N7:0", destination="N7:1"),
        _mov_record(source="N7:2", destination="N7:1"),
        _mov_record(source="N7:0", destination="N7:3"),
    ]

    evidence = [
        scan_controlled_mov_instructions(
            variant,
            include_private_text=True,
        )[0]
        for variant in variants
    ]

    assert {item.selector for item in evidence} == {0x1C}
    assert len({item.selector_offset for item in evidence}) == 1
    assert [item.operands[0].value for item in evidence] == [
        "N7:0",
        "N7:2",
        "N7:0",
    ]
    assert [item.operands[1].value for item in evidence] == [
        "N7:1",
        "N7:1",
        "N7:3",
    ]


def test_combined_scanner_returns_xic_before_mov() -> None:
    result = scan_controlled_instructions(
        _record(operand="B3:0/0", selector=0x39)
        + _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )

    assert [item.mnemonic for item in result] == ["XIC", "MOV"]
