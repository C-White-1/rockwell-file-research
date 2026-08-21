"""Tests for controlled-profile RSS instruction recognition."""

import zlib

from rockwell_file_research.rss.instruction_evidence import (
    scan_controlled_abs_instructions,
    scan_controlled_add_instructions,
    scan_controlled_and_instructions,
    scan_controlled_clr_instructions,
    scan_controlled_ctd_instructions,
    scan_controlled_ctu_instructions,
    scan_controlled_div_instructions,
    scan_controlled_equ_instructions,
    scan_controlled_instructions,
    scan_controlled_les_instructions,
    scan_controlled_mov_instructions,
    scan_controlled_mul_instructions,
    scan_controlled_neg_instructions,
    scan_controlled_neq_instructions,
    scan_controlled_not_instructions,
    scan_controlled_or_instructions,
    scan_controlled_res_instructions,
    scan_controlled_rto_instructions,
    scan_controlled_simple_bit_instructions,
    scan_controlled_sqr_instructions,
    scan_controlled_sub_instructions,
    scan_controlled_tof_instructions,
    scan_controlled_ton_instructions,
    scan_controlled_xor_instructions,
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


def _clr_record(destination: str) -> bytes:
    encoded = destination.encode("ascii")
    return (
        b"\x02\x00"
        + bytes([len(encoded)])
        + encoded
        + b"\x01\x3f\x00\x00\x14"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _add_record(*, source_a: str, source_b: str, destination: str) -> bytes:
    fields = [
        source_a.encode("ascii"),
        source_b.encode("ascii"),
        destination.encode("ascii"),
    ]
    return (
        b"\x06\x00"
        + b"".join(bytes([len(field)]) + field + b"\x01\x3f" for field in fields)
        + b"\x00\x00\x27"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _timer_record(
    *,
    selector: int,
    timer: str,
    time_base: str = "1.0",
    preset: str = "5",
    accumulator: str = "0",
) -> bytes:
    fields = [
        timer.encode("ascii"),
        time_base.encode("ascii"),
        preset.encode("ascii"),
        accumulator.encode("ascii"),
    ]
    return (
        b"\x04\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00"
        + bytes([selector])
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _res_record(operand: str) -> bytes:
    encoded = operand.encode("ascii")
    return (
        b"\x01\x00"
        + bytes([len(encoded)])
        + encoded
        + b"\x00\x00\x13"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _counter_record(
    *,
    selector: int,
    counter: str,
    preset: str = "3",
    accumulator: str = "0",
) -> bytes:
    fields = [
        counter.encode("ascii"),
        preset.encode("ascii"),
        accumulator.encode("ascii"),
    ]
    return (
        b"\x03\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00"
        + bytes([selector])
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


def test_controlled_add_exposes_three_ordered_operand_roles() -> None:
    result = scan_controlled_add_instructions(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2"),
        include_private_text=True,
    )

    assert len(result) == 1
    assert result[0].selector == 0x27
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source_a", "N7:0"),
        ("source_b", "N7:1"),
        ("destination", "N7:2"),
    ]


def test_controlled_clr_exposes_destination_operand() -> None:
    result = scan_controlled_clr_instructions(
        _clr_record("N7:0"),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("CLR", 0x14)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("destination", "N7:0")
    ]


def test_neg_differs_from_mov_only_by_controlled_selector() -> None:
    mov = scan_controlled_mov_instructions(
        _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )[0]
    neg_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    neg_payload[-8] = 0x1E
    neg = scan_controlled_neg_instructions(
        bytes(neg_payload),
        include_private_text=True,
    )[0]

    assert (mov.mnemonic, mov.selector) == ("MOV", 0x1C)
    assert (neg.mnemonic, neg.selector) == ("NEG", 0x1E)
    assert mov.selector_offset == neg.selector_offset
    assert mov.operands == neg.operands


def test_sqr_differs_from_mov_only_by_controlled_selector() -> None:
    mov = scan_controlled_mov_instructions(
        _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )[0]
    sqr_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    sqr_payload[-8] = 0x46
    sqr = scan_controlled_sqr_instructions(
        bytes(sqr_payload),
        include_private_text=True,
    )[0]

    assert (mov.mnemonic, mov.selector) == ("MOV", 0x1C)
    assert (sqr.mnemonic, sqr.selector) == ("SQR", 0x46)
    assert mov.selector_offset == sqr.selector_offset
    assert mov.operands == sqr.operands


def test_abs_differs_from_mov_only_by_controlled_selector() -> None:
    mov = scan_controlled_mov_instructions(
        _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )[0]
    abs_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    abs_payload[-8] = 0x98
    absolute = scan_controlled_abs_instructions(
        bytes(abs_payload),
        include_private_text=True,
    )[0]

    assert (mov.mnemonic, mov.selector) == ("MOV", 0x1C)
    assert (absolute.mnemonic, absolute.selector) == ("ABS", 0x98)
    assert mov.selector_offset == absolute.selector_offset
    assert mov.operands == absolute.operands


def test_not_differs_from_mov_only_by_controlled_selector() -> None:
    mov = scan_controlled_mov_instructions(
        _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )[0]
    not_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    not_payload[-8] = 0x1B
    bitwise_not = scan_controlled_not_instructions(
        bytes(not_payload),
        include_private_text=True,
    )[0]

    assert (mov.mnemonic, mov.selector) == ("MOV", 0x1C)
    assert (bitwise_not.mnemonic, bitwise_not.selector) == ("NOT", 0x1B)
    assert mov.selector_offset == bitwise_not.selector_offset
    assert mov.operands == bitwise_not.operands


def test_equ_uses_two_comparison_source_roles() -> None:
    equ_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    equ_payload[-8] = 0x32
    result = scan_controlled_equ_instructions(
        bytes(equ_payload),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("EQU", 0x32)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source_a", "N7:0"),
        ("source_b", "N7:1"),
    ]


def test_neq_differs_from_equ_only_by_controlled_selector() -> None:
    equ_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    equ_payload[-8] = 0x32
    equ = scan_controlled_equ_instructions(
        bytes(equ_payload),
        include_private_text=True,
    )[0]
    neq_payload = bytearray(equ_payload)
    neq_payload[-8] = 0x33
    neq = scan_controlled_neq_instructions(
        bytes(neq_payload),
        include_private_text=True,
    )[0]

    assert (equ.mnemonic, equ.selector) == ("EQU", 0x32)
    assert (neq.mnemonic, neq.selector) == ("NEQ", 0x33)
    assert equ.selector_offset == neq.selector_offset
    assert equ.operands == neq.operands


def test_les_uses_two_comparison_source_roles() -> None:
    les_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    les_payload[-8] = 0x36
    result = scan_controlled_les_instructions(
        bytes(les_payload),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("LES", 0x36)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source_a", "N7:0"),
        ("source_b", "N7:1"),
    ]


def test_and_differs_from_add_only_by_controlled_selector() -> None:
    add = scan_controlled_add_instructions(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2"),
        include_private_text=True,
    )[0]
    and_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    and_payload[-8] = 0x23
    bitwise_and = scan_controlled_and_instructions(
        bytes(and_payload),
        include_private_text=True,
    )[0]

    assert (add.mnemonic, add.selector) == ("ADD", 0x27)
    assert (bitwise_and.mnemonic, bitwise_and.selector) == ("AND", 0x23)
    assert add.selector_offset == bitwise_and.selector_offset
    assert add.operands == bitwise_and.operands


def test_or_differs_from_and_only_by_controlled_selector() -> None:
    and_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    and_payload[-8] = 0x23
    bitwise_and = scan_controlled_and_instructions(
        bytes(and_payload),
        include_private_text=True,
    )[0]
    or_payload = bytearray(and_payload)
    or_payload[-8] = 0x24
    bitwise_or = scan_controlled_or_instructions(
        bytes(or_payload),
        include_private_text=True,
    )[0]

    assert (bitwise_and.mnemonic, bitwise_and.selector) == ("AND", 0x23)
    assert (bitwise_or.mnemonic, bitwise_or.selector) == ("OR", 0x24)
    assert bitwise_and.selector_offset == bitwise_or.selector_offset
    assert bitwise_and.operands == bitwise_or.operands


def test_xor_differs_from_and_only_by_controlled_selector() -> None:
    and_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    and_payload[-8] = 0x23
    bitwise_and = scan_controlled_and_instructions(
        bytes(and_payload),
        include_private_text=True,
    )[0]
    xor_payload = bytearray(and_payload)
    xor_payload[-8] = 0x25
    bitwise_xor = scan_controlled_xor_instructions(
        bytes(xor_payload),
        include_private_text=True,
    )[0]

    assert (bitwise_and.mnemonic, bitwise_and.selector) == ("AND", 0x23)
    assert (bitwise_xor.mnemonic, bitwise_xor.selector) == ("XOR", 0x25)
    assert bitwise_and.selector_offset == bitwise_xor.selector_offset
    assert bitwise_and.operands == bitwise_xor.operands


def test_add_selector_is_stable_across_independent_operand_changes() -> None:
    variants = [
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2"),
        _add_record(source_a="N7:3", source_b="N7:1", destination="N7:2"),
        _add_record(source_a="N7:0", source_b="N7:4", destination="N7:2"),
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:5"),
    ]

    evidence = [
        scan_controlled_add_instructions(
            variant,
            include_private_text=True,
        )[0]
        for variant in variants
    ]

    assert {item.selector for item in evidence} == {0x27}
    assert len({item.selector_offset for item in evidence}) == 1
    assert [tuple(operand.value for operand in item.operands) for item in evidence] == [
        ("N7:0", "N7:1", "N7:2"),
        ("N7:3", "N7:1", "N7:2"),
        ("N7:0", "N7:4", "N7:2"),
        ("N7:0", "N7:1", "N7:5"),
    ]


def test_sub_differs_from_add_only_by_controlled_selector() -> None:
    add = scan_controlled_add_instructions(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2"),
        include_private_text=True,
    )[0]
    sub_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    sub_payload[-8] = 0x28
    sub = scan_controlled_sub_instructions(
        bytes(sub_payload),
        include_private_text=True,
    )[0]

    assert (add.mnemonic, add.selector) == ("ADD", 0x27)
    assert (sub.mnemonic, sub.selector) == ("SUB", 0x28)
    assert add.selector_offset == sub.selector_offset
    assert add.operands == sub.operands


def test_mul_differs_from_add_only_by_controlled_selector() -> None:
    add = scan_controlled_add_instructions(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2"),
        include_private_text=True,
    )[0]
    mul_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    mul_payload[-8] = 0x29
    mul = scan_controlled_mul_instructions(
        bytes(mul_payload),
        include_private_text=True,
    )[0]

    assert (add.mnemonic, add.selector) == ("ADD", 0x27)
    assert (mul.mnemonic, mul.selector) == ("MUL", 0x29)
    assert add.selector_offset == mul.selector_offset
    assert add.operands == mul.operands


def test_div_differs_from_add_only_by_controlled_selector() -> None:
    add = scan_controlled_add_instructions(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2"),
        include_private_text=True,
    )[0]
    div_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    div_payload[-8] = 0x2A
    div = scan_controlled_div_instructions(
        bytes(div_payload),
        include_private_text=True,
    )[0]

    assert (add.mnemonic, add.selector) == ("ADD", 0x27)
    assert (div.mnemonic, div.selector) == ("DIV", 0x2A)
    assert add.selector_offset == div.selector_offset
    assert add.operands == div.operands


def test_combined_scanner_returns_xic_before_mov() -> None:
    result = scan_controlled_instructions(
        _record(operand="B3:0/0", selector=0x39)
        + _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )

    assert [item.mnemonic for item in result] == ["XIC", "MOV"]


def test_controlled_ton_exposes_ordered_structured_fields() -> None:
    result = scan_controlled_ton_instructions(
        _timer_record(selector=0xA7, timer="T4:0"),
        include_private_text=True,
    )

    assert len(result) == 1
    assert result[0].selector == 0xA7
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("timer", "T4:0"),
        ("time_base", "1.0"),
        ("preset", "5"),
        ("accumulator", "0"),
    ]


def test_ton_selector_is_stable_across_timer_and_preset_changes() -> None:
    variants = [
        _timer_record(selector=0xA7, timer="T4:0", preset="5"),
        _timer_record(selector=0xA7, timer="T4:0", preset="7"),
        _timer_record(selector=0xA7, timer="T4:1", preset="5"),
    ]

    evidence = [
        scan_controlled_ton_instructions(
            variant,
            include_private_text=True,
        )[0]
        for variant in variants
    ]

    assert {item.selector for item in evidence} == {0xA7}
    assert len({item.selector_offset for item in evidence}) == 1
    assert [item.operands[0].value for item in evidence] == [
        "T4:0",
        "T4:0",
        "T4:1",
    ]
    assert [item.operands[2].value for item in evidence] == ["5", "7", "5"]


def test_ton_rejects_uncontrolled_time_base_and_nonzero_accumulator() -> None:
    assert not scan_controlled_ton_instructions(
        _timer_record(selector=0xA7, timer="T4:0", time_base="0.01")
    )
    assert not scan_controlled_ton_instructions(
        _timer_record(selector=0xA7, timer="T4:0", accumulator="1")
    )


def test_rto_differs_from_ton_only_by_controlled_selector() -> None:
    ton = scan_controlled_ton_instructions(
        _timer_record(selector=0xA7, timer="T4:0"),
        include_private_text=True,
    )[0]
    rto = scan_controlled_rto_instructions(
        _timer_record(selector=0xA3, timer="T4:0"),
        include_private_text=True,
    )[0]

    assert (ton.mnemonic, ton.selector) == ("TON", 0xA7)
    assert (rto.mnemonic, rto.selector) == ("RTO", 0xA3)
    assert ton.selector_offset == rto.selector_offset
    assert ton.operands == rto.operands


def test_tof_differs_from_ton_only_by_controlled_selector() -> None:
    ton = scan_controlled_ton_instructions(
        _timer_record(selector=0xA7, timer="T4:0"),
        include_private_text=True,
    )[0]
    tof = scan_controlled_tof_instructions(
        _timer_record(selector=0xA6, timer="T4:0"),
        include_private_text=True,
    )[0]

    assert (ton.mnemonic, ton.selector) == ("TON", 0xA7)
    assert (tof.mnemonic, tof.selector) == ("TOF", 0xA6)
    assert ton.selector_offset == tof.selector_offset
    assert ton.operands == tof.operands


def test_controlled_res_supports_timer_and_counter_operands() -> None:
    timer = scan_controlled_res_instructions(
        _res_record("T4:0"),
        include_private_text=True,
    )[0]
    counter = scan_controlled_res_instructions(
        _res_record("C5:0"),
        include_private_text=True,
    )[0]

    assert timer.mnemonic == counter.mnemonic == "RES"
    assert timer.selector == counter.selector == 0x13
    assert timer.selector_offset == counter.selector_offset
    assert timer.operands[0].value == "T4:0"
    assert counter.operands[0].value == "C5:0"


def test_res_rejects_uncontrolled_operand_family() -> None:
    assert not scan_controlled_res_instructions(_res_record("N7:0"))


def test_controlled_ctu_exposes_ordered_structured_fields() -> None:
    result = scan_controlled_ctu_instructions(
        _counter_record(selector=0x11, counter="C5:0"),
        include_private_text=True,
    )

    assert len(result) == 1
    assert result[0].selector == 0x11
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("counter", "C5:0"),
        ("preset", "3"),
        ("accumulator", "0"),
    ]


def test_ctu_selector_is_stable_across_counter_and_preset_changes() -> None:
    variants = [
        _counter_record(selector=0x11, counter="C5:0", preset="3"),
        _counter_record(selector=0x11, counter="C5:0", preset="5"),
        _counter_record(selector=0x11, counter="C5:1", preset="3"),
    ]

    evidence = [
        scan_controlled_ctu_instructions(
            variant,
            include_private_text=True,
        )[0]
        for variant in variants
    ]

    assert {item.selector for item in evidence} == {0x11}
    assert len({item.selector_offset for item in evidence}) == 1
    assert [item.operands[0].value for item in evidence] == [
        "C5:0",
        "C5:0",
        "C5:1",
    ]
    assert [item.operands[1].value for item in evidence] == ["3", "5", "3"]


def test_ctu_rejects_nonzero_accumulator() -> None:
    assert not scan_controlled_ctu_instructions(
        _counter_record(selector=0x11, counter="C5:0", accumulator="1")
    )


def test_ctd_differs_from_ctu_only_by_controlled_selector() -> None:
    ctu = scan_controlled_ctu_instructions(
        _counter_record(selector=0x11, counter="C5:0"),
        include_private_text=True,
    )[0]
    ctd = scan_controlled_ctd_instructions(
        _counter_record(selector=0x12, counter="C5:0"),
        include_private_text=True,
    )[0]

    assert (ctu.mnemonic, ctu.selector) == ("CTU", 0x11)
    assert (ctd.mnemonic, ctd.selector) == ("CTD", 0x12)
    assert ctu.selector_offset == ctd.selector_offset
    assert ctu.operands == ctd.operands
