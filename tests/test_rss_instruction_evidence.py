"""Tests for controlled-profile RSS instruction recognition."""

import zlib

from rockwell_file_research.rss.instruction_evidence import (
    scan_controlled_abs_instructions,
    scan_controlled_add_instructions,
    scan_controlled_and_instructions,
    scan_controlled_bsl_instructions,
    scan_controlled_bsr_instructions,
    scan_controlled_clr_instructions,
    scan_controlled_cop_instructions,
    scan_controlled_ctd_instructions,
    scan_controlled_ctu_instructions,
    scan_controlled_div_instructions,
    scan_controlled_equ_instructions,
    scan_controlled_ffl_instructions,
    scan_controlled_ffu_instructions,
    scan_controlled_fll_instructions,
    scan_controlled_frd_instructions,
    scan_controlled_geq_instructions,
    scan_controlled_grt_instructions,
    scan_controlled_instructions,
    scan_controlled_jmp_instructions,
    scan_controlled_jsr_instructions,
    scan_controlled_lbl_instructions,
    scan_controlled_leq_instructions,
    scan_controlled_les_instructions,
    scan_controlled_lfl_instructions,
    scan_controlled_lfu_instructions,
    scan_controlled_lim_instructions,
    scan_controlled_mcr_instructions,
    scan_controlled_meq_instructions,
    scan_controlled_mov_instructions,
    scan_controlled_msg_instructions,
    scan_controlled_mul_instructions,
    scan_controlled_mvm_instructions,
    scan_controlled_neg_instructions,
    scan_controlled_neq_instructions,
    scan_controlled_not_instructions,
    scan_controlled_ons_instructions,
    scan_controlled_or_instructions,
    scan_controlled_osf_instructions,
    scan_controlled_osr_instructions,
    scan_controlled_pid_instructions,
    scan_controlled_pto_instructions,
    scan_controlled_pwm_instructions,
    scan_controlled_res_instructions,
    scan_controlled_ret_instructions,
    scan_controlled_rto_instructions,
    scan_controlled_sbr_instructions,
    scan_controlled_scl_instructions,
    scan_controlled_scp_instructions,
    scan_controlled_simple_bit_instructions,
    scan_controlled_sqc_instructions,
    scan_controlled_sql_instructions,
    scan_controlled_sqo_instructions,
    scan_controlled_sqr_instructions,
    scan_controlled_sub_instructions,
    scan_controlled_sus_instructions,
    scan_controlled_swp_instructions,
    scan_controlled_tnd_instructions,
    scan_controlled_tod_instructions,
    scan_controlled_tof_instructions,
    scan_controlled_ton_instructions,
    scan_controlled_uid_instructions,
    scan_controlled_uie_instructions,
    scan_controlled_uif_instructions,
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


def _edge_output_record(*, selector: int) -> bytes:
    fields = (b"B3:0/1", b"B3:0/2")
    return (
        b"\x02\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00"
        + bytes([selector])
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _shift_record(*, selector: int) -> bytes:
    fields = (b"#B3:1", b"R6:0", b"B3:0/1", b"16")
    return (
        b"\x04\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00"
        + bytes([selector])
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _sqc_record() -> bytes:
    fields = (b"#N7:10", b"00FFh", b"N7:0", b"R6:0", b"3", b"0")
    return (
        b"\x06\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00\x2e"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _sql_record() -> bytes:
    fields = (b"#N7:10", b"N7:0", b"R6:0", b"3", b"0")
    return (
        b"\x05\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00\x40"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _sqo_record() -> bytes:
    fields = (b"#N7:10", b"00FFh", b"N7:0", b"R6:0", b"3", b"0")
    return (
        b"\x06\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00\x2d"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _pid_record() -> bytes:
    fields = (b"PD9:0", b"N7:0", b"N7:1")
    return (
        b"\x04\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x01\x3f\x00\x00\x9f"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _msg_record() -> bytes:
    operand = b"MG10:0"
    return (
        b"\x04\x00"
        + bytes([len(operand)])
        + operand
        + b"\x01\x3f\x01\x3f\x01\x3f\x00\x00\xb3"
        + bytes(17)
        + b"\x0b500CPU Read"
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


def _scp_record(fields: list[str]) -> bytes:
    encoded = [field.encode("ascii") for field in fields]
    return (
        b"\x0c\x00"
        + b"".join(bytes([len(field)]) + field + b"\x01\x3f" for field in encoded)
        + b"\x00\x00\x95"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _scl_record(fields: list[str]) -> bytes:
    encoded = [field.encode("ascii") for field in fields]
    return (
        b"\x08\x00"
        + b"".join(bytes([len(field)]) + field + b"\x01\x3f" for field in encoded)
        + b"\x00\x00\x45"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _swp_record(*, source: str = "#N7:0", length: str = "3") -> bytes:
    source_bytes = source.encode("ascii")
    length_bytes = length.encode("ascii")
    return (
        b"\x02\x00"
        + bytes([len(source_bytes)])
        + source_bytes
        + bytes([len(length_bytes)])
        + length_bytes
        + b"\x00\x00\x96"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _cop_record(
    *,
    source: str = "#N7:0",
    destination: str = "#N7:10",
    length: str = "3",
) -> bytes:
    fields = [
        source.encode("ascii"),
        destination.encode("ascii"),
        length.encode("ascii"),
    ]
    return (
        b"\x03\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00\x22"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _fll_record(
    *,
    source: str = "N7:0",
    destination: str = "#N7:10",
    length: str = "3",
) -> bytes:
    fields = [
        source.encode("ascii"),
        destination.encode("ascii"),
        length.encode("ascii"),
    ]
    return (
        b"\x03\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00\x21"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _ffl_record() -> bytes:
    fields = [
        b"N7:0",
        b"#N7:10",
        b"R6:0",
        b"3",
        b"0",
    ]
    return (
        b"\x05\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00\x41"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _ffu_record() -> bytes:
    fields = [
        b"#N7:10",
        b"N7:0",
        b"R6:0",
        b"3",
        b"0",
    ]
    return (
        b"\x05\x00"
        + b"".join(bytes([len(field)]) + field for field in fields)
        + b"\x00\x00\x42"
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _lfl_record() -> bytes:
    record = bytearray(_ffl_record())
    record[-8] = 0x43
    return bytes(record)


def _lfu_record() -> bytes:
    record = bytearray(_ffu_record())
    record[-8] = 0x44
    return bytes(record)


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


def _label_record(*, operand: str, selector: int) -> bytes:
    encoded = operand.encode("ascii")
    return (
        b"\x01\x00"
        + bytes([len(encoded)])
        + encoded
        + b"\x00\x00"
        + bytes([selector])
        + b"\x00\x00\x00\x00\x00\x0b\x80"
    )


def _zero_operand_record(selector: int) -> bytes:
    return b"\x00\x00\x00\x00" + bytes([selector]) + b"\x00\x00\x00\x00\x00\x0b\x80"


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


def test_ons_exposes_storage_bit_role_under_its_own_profile() -> None:
    result = scan_controlled_ons_instructions(
        _record(operand="B3:0/1", selector=0xAB),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("ONS", 0xAB)
    assert result[0].evidence_profile.endswith("/ons/v1")
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("storage_bit", "B3:0/1"),
    ]


def test_osr_exposes_ordered_storage_and_output_bits() -> None:
    result = scan_controlled_osr_instructions(
        _edge_output_record(selector=0x9E),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("OSR", 0x9E)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("storage_bit", "B3:0/1"),
        ("output_bit", "B3:0/2"),
    ]


def test_osf_differs_from_osr_only_by_controlled_selector() -> None:
    osf = scan_controlled_osf_instructions(
        _edge_output_record(selector=0x9D),
        include_private_text=True,
    )[0]
    osr = scan_controlled_osr_instructions(
        _edge_output_record(selector=0x9E),
        include_private_text=True,
    )[0]

    assert (osf.mnemonic, osf.selector) == ("OSF", 0x9D)
    assert (osr.mnemonic, osr.selector) == ("OSR", 0x9E)
    assert osf.selector_offset == osr.selector_offset
    assert osf.operands == osr.operands


def test_bsl_exposes_ordered_shift_operands() -> None:
    result = scan_controlled_bsl_instructions(
        _shift_record(selector=0x2C),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("BSL", 0x2C)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("file", "#B3:1"),
        ("control", "R6:0"),
        ("bit_address", "B3:0/1"),
        ("length", "16"),
    ]


def test_bsr_differs_from_bsl_only_by_controlled_selector() -> None:
    bsr = scan_controlled_bsr_instructions(
        _shift_record(selector=0x2B),
        include_private_text=True,
    )[0]
    bsl = scan_controlled_bsl_instructions(
        _shift_record(selector=0x2C),
        include_private_text=True,
    )[0]

    assert (bsr.mnemonic, bsr.selector) == ("BSR", 0x2B)
    assert (bsl.mnemonic, bsl.selector) == ("BSL", 0x2C)
    assert bsr.selector_offset == bsl.selector_offset
    assert bsr.operands == bsl.operands


def test_sqc_exposes_ordered_sequencer_compare_operands() -> None:
    result = scan_controlled_sqc_instructions(
        _sqc_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SQC", 0x2E)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("file", "#N7:10"),
        ("mask", "00FFh"),
        ("source", "N7:0"),
        ("control", "R6:0"),
        ("length", "3"),
        ("position", "0"),
    ]


def test_sql_exposes_ordered_sequencer_load_operands() -> None:
    result = scan_controlled_sql_instructions(
        _sql_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SQL", 0x40)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("file", "#N7:10"),
        ("source", "N7:0"),
        ("control", "R6:0"),
        ("length", "3"),
        ("position", "0"),
    ]


def test_sqo_exposes_ordered_sequencer_output_operands() -> None:
    result = scan_controlled_sqo_instructions(
        _sqo_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SQO", 0x2D)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("file", "#N7:10"),
        ("mask", "00FFh"),
        ("destination", "N7:0"),
        ("control", "R6:0"),
        ("length", "3"),
        ("position", "0"),
    ]


def test_pid_exposes_ordered_control_operands() -> None:
    result = scan_controlled_pid_instructions(
        _pid_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("PID", 0x9F)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("pid_file", "PD9:0"),
        ("process_variable", "N7:0"),
        ("control_variable", "N7:1"),
    ]


def test_msg_exposes_file_but_not_unresolved_setup_fields() -> None:
    result = scan_controlled_msg_instructions(
        _msg_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("MSG", 0xB3)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("msg_file", "MG10:0"),
    ]


def test_pto_exposes_pulse_train_output_number() -> None:
    result = scan_controlled_pto_instructions(
        _record(operand="0", selector=0xA0),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("PTO", 0xA0)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("pto_number", "0"),
    ]


def test_pwm_differs_from_pto_only_by_controlled_selector_and_role() -> None:
    pwm = scan_controlled_pwm_instructions(
        _record(operand="0", selector=0xA1),
        include_private_text=True,
    )[0]
    pto = scan_controlled_pto_instructions(
        _record(operand="0", selector=0xA0),
        include_private_text=True,
    )[0]

    assert (pwm.mnemonic, pwm.selector) == ("PWM", 0xA1)
    assert (pto.mnemonic, pto.selector) == ("PTO", 0xA0)
    assert pwm.selector_offset == pto.selector_offset
    assert [(item.role, item.value) for item in pwm.operands] == [
        ("pwm_number", "0"),
    ]
    assert pwm.operands[0].value == pto.operands[0].value


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


def test_leq_differs_from_les_only_by_controlled_selector() -> None:
    les_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    les_payload[-8] = 0x36
    les = scan_controlled_les_instructions(
        bytes(les_payload),
        include_private_text=True,
    )[0]
    leq_payload = bytearray(les_payload)
    leq_payload[-8] = 0x37
    leq = scan_controlled_leq_instructions(
        bytes(leq_payload),
        include_private_text=True,
    )[0]

    assert (les.mnemonic, les.selector) == ("LES", 0x36)
    assert (leq.mnemonic, leq.selector) == ("LEQ", 0x37)
    assert les.selector_offset == leq.selector_offset
    assert les.operands == leq.operands


def test_grt_uses_two_comparison_source_roles() -> None:
    grt_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    grt_payload[-8] = 0x34
    result = scan_controlled_grt_instructions(
        bytes(grt_payload),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("GRT", 0x34)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source_a", "N7:0"),
        ("source_b", "N7:1"),
    ]


def test_geq_differs_from_grt_only_by_controlled_selector() -> None:
    grt_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    grt_payload[-8] = 0x34
    grt = scan_controlled_grt_instructions(
        bytes(grt_payload),
        include_private_text=True,
    )[0]
    geq_payload = bytearray(grt_payload)
    geq_payload[-8] = 0x35
    geq = scan_controlled_geq_instructions(
        bytes(geq_payload),
        include_private_text=True,
    )[0]

    assert (grt.mnemonic, grt.selector) == ("GRT", 0x34)
    assert (geq.mnemonic, geq.selector) == ("GEQ", 0x35)
    assert grt.selector_offset == geq.selector_offset
    assert grt.operands == geq.operands


def test_meq_exposes_source_mask_and_compare_roles() -> None:
    meq_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    meq_payload[-8] = 0x38
    result = scan_controlled_meq_instructions(
        bytes(meq_payload),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("MEQ", 0x38)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "N7:0"),
        ("mask", "N7:1"),
        ("compare", "N7:2"),
    ]


def test_mvm_exposes_source_normalized_mask_and_destination_roles() -> None:
    mvm_payload = bytearray(
        _add_record(source_a="N7:0", source_b="00FFh", destination="N7:1")
    )
    mvm_payload[-8] = 0x26
    result = scan_controlled_mvm_instructions(
        bytes(mvm_payload),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("MVM", 0x26)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "N7:0"),
        ("mask", "00FFh"),
        ("destination", "N7:1"),
    ]


def test_lim_exposes_low_test_and_high_roles() -> None:
    lim_payload = bytearray(
        _add_record(source_a="N7:0", source_b="N7:1", destination="N7:2")
    )
    lim_payload[-8] = 0x3F
    result = scan_controlled_lim_instructions(
        bytes(lim_payload),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("LIM", 0x3F)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("low_limit", "N7:0"),
        ("test", "N7:1"),
        ("high_limit", "N7:2"),
    ]


def test_scp_exposes_six_ordered_scaling_roles() -> None:
    result = scan_controlled_scp_instructions(
        _scp_record([f"N7:{index}" for index in range(6)]),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SCP", 0x95)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("input", "N7:0"),
        ("input_min", "N7:1"),
        ("input_max", "N7:2"),
        ("scaled_min", "N7:3"),
        ("scaled_max", "N7:4"),
        ("output", "N7:5"),
    ]


def test_scl_exposes_four_ordered_scaling_roles() -> None:
    result = scan_controlled_scl_instructions(
        _scl_record([f"N7:{index}" for index in range(4)]),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SCL", 0x45)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "N7:0"),
        ("rate", "N7:1"),
        ("offset", "N7:2"),
        ("destination", "N7:3"),
    ]


def test_swp_exposes_file_source_and_literal_length() -> None:
    result = scan_controlled_swp_instructions(
        _swp_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SWP", 0x96)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "#N7:0"),
        ("length", "3"),
    ]


def test_swp_rejects_non_file_source_and_non_integer_length() -> None:
    assert not scan_controlled_swp_instructions(_swp_record(source="N7:0"))
    assert not scan_controlled_swp_instructions(_swp_record(length="N7:1"))


def test_cop_exposes_two_file_addresses_and_literal_length() -> None:
    result = scan_controlled_cop_instructions(
        _cop_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("COP", 0x22)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "#N7:0"),
        ("destination", "#N7:10"),
        ("length", "3"),
    ]


def test_fll_exposes_scalar_source_file_destination_and_length() -> None:
    result = scan_controlled_fll_instructions(
        _fll_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("FLL", 0x21)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "N7:0"),
        ("destination", "#N7:10"),
        ("length", "3"),
    ]


def test_ffl_exposes_five_ordered_fifo_fields() -> None:
    result = scan_controlled_ffl_instructions(
        _ffl_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("FFL", 0x41)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "N7:0"),
        ("fifo", "#N7:10"),
        ("control", "R6:0"),
        ("length", "3"),
        ("position", "0"),
    ]


def test_ffu_exposes_reversed_fifo_data_flow_roles() -> None:
    result = scan_controlled_ffu_instructions(
        _ffu_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("FFU", 0x42)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("fifo", "#N7:10"),
        ("destination", "N7:0"),
        ("control", "R6:0"),
        ("length", "3"),
        ("position", "0"),
    ]


def test_lfl_differs_from_ffl_only_by_selector_and_lifo_role() -> None:
    result = scan_controlled_lfl_instructions(
        _lfl_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("LFL", 0x43)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("source", "N7:0"),
        ("lifo", "#N7:10"),
        ("control", "R6:0"),
        ("length", "3"),
        ("position", "0"),
    ]


def test_lfu_differs_from_ffu_only_by_selector_and_lifo_role() -> None:
    result = scan_controlled_lfu_instructions(
        _lfu_record(),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("LFU", 0x44)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("lifo", "#N7:10"),
        ("destination", "N7:0"),
        ("control", "R6:0"),
        ("length", "3"),
        ("position", "0"),
    ]


def test_tod_differs_from_mov_only_by_controlled_selector() -> None:
    mov = scan_controlled_mov_instructions(
        _mov_record(source="N7:0", destination="N7:1"),
        include_private_text=True,
    )[0]
    tod_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    tod_payload[-8] = 0x17
    tod = scan_controlled_tod_instructions(
        bytes(tod_payload),
        include_private_text=True,
    )[0]

    assert (mov.mnemonic, mov.selector) == ("MOV", 0x1C)
    assert (tod.mnemonic, tod.selector) == ("TOD", 0x17)
    assert mov.selector_offset == tod.selector_offset
    assert mov.operands == tod.operands


def test_frd_differs_from_tod_only_by_controlled_selector() -> None:
    tod_payload = bytearray(_mov_record(source="N7:0", destination="N7:1"))
    tod_payload[-8] = 0x17
    tod = scan_controlled_tod_instructions(
        bytes(tod_payload),
        include_private_text=True,
    )[0]
    frd_payload = bytearray(tod_payload)
    frd_payload[-8] = 0x18
    frd = scan_controlled_frd_instructions(
        bytes(frd_payload),
        include_private_text=True,
    )[0]

    assert (tod.mnemonic, tod.selector) == ("TOD", 0x17)
    assert (frd.mnemonic, frd.selector) == ("FRD", 0x18)
    assert tod.selector_offset == frd.selector_offset
    assert tod.operands == frd.operands


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


def test_jmp_exposes_normalized_program_label_operand() -> None:
    result = scan_controlled_jmp_instructions(
        _label_record(operand="Q2:1", selector=0x16),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("JMP", 0x16)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("label", "Q2:1"),
    ]


def test_jmp_rejects_non_label_operand_family() -> None:
    assert not scan_controlled_jmp_instructions(
        _label_record(operand="N7:1", selector=0x16)
    )


def test_lbl_differs_from_jmp_only_by_controlled_selector() -> None:
    jmp = scan_controlled_jmp_instructions(
        _label_record(operand="Q2:1", selector=0x16),
        include_private_text=True,
    )[0]
    lbl = scan_controlled_lbl_instructions(
        _label_record(operand="Q2:1", selector=0x3B),
        include_private_text=True,
    )[0]

    assert (jmp.mnemonic, jmp.selector) == ("JMP", 0x16)
    assert (lbl.mnemonic, lbl.selector) == ("LBL", 0x3B)
    assert jmp.selector_offset == lbl.selector_offset
    assert jmp.operands == lbl.operands


def test_jsr_exposes_normalized_subroutine_file_operand() -> None:
    result = scan_controlled_jsr_instructions(
        _label_record(operand="U:3", selector=0x15),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("JSR", 0x15)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("subroutine", "U:3"),
    ]


def test_program_control_operands_remain_family_specific() -> None:
    assert not scan_controlled_jsr_instructions(
        _label_record(operand="Q2:1", selector=0x15)
    )
    assert not scan_controlled_jmp_instructions(
        _label_record(operand="U:3", selector=0x16)
    )


def test_sus_exposes_literal_suspend_identifier() -> None:
    result = scan_controlled_sus_instructions(
        _label_record(operand="1", selector=0x1F),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SUS", 0x1F)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("suspend_id", "1"),
    ]


def test_sus_rejects_non_integer_identifier() -> None:
    assert not scan_controlled_sus_instructions(
        _label_record(operand="N7:1", selector=0x1F)
    )


def test_uie_exposes_literal_interrupt_type_mask() -> None:
    result = scan_controlled_uie_instructions(
        _label_record(operand="1", selector=0xA9),
        include_private_text=True,
    )

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("UIE", 0xA9)
    assert [(item.role, item.value) for item in result[0].operands] == [
        ("interrupt_types", "1"),
    ]


def test_uid_differs_from_uie_only_by_controlled_selector() -> None:
    uid = scan_controlled_uid_instructions(
        _label_record(operand="1", selector=0xA8),
        include_private_text=True,
    )[0]
    uie = scan_controlled_uie_instructions(
        _label_record(operand="1", selector=0xA9),
        include_private_text=True,
    )[0]

    assert (uid.mnemonic, uid.selector) == ("UID", 0xA8)
    assert (uie.mnemonic, uie.selector) == ("UIE", 0xA9)
    assert uid.selector_offset == uie.selector_offset
    assert uid.operands == uie.operands


def test_uif_completes_contiguous_interrupt_selector_family() -> None:
    uid = scan_controlled_uid_instructions(
        _label_record(operand="1", selector=0xA8),
        include_private_text=True,
    )[0]
    uie = scan_controlled_uie_instructions(
        _label_record(operand="1", selector=0xA9),
        include_private_text=True,
    )[0]
    uif = scan_controlled_uif_instructions(
        _label_record(operand="1", selector=0xAA),
        include_private_text=True,
    )[0]

    assert [(item.mnemonic, item.selector) for item in (uid, uie, uif)] == [
        ("UID", 0xA8),
        ("UIE", 0xA9),
        ("UIF", 0xAA),
    ]
    assert uid.selector_offset == uie.selector_offset == uif.selector_offset
    assert uid.operands == uie.operands == uif.operands


def test_sbr_is_a_zero_operand_program_control_marker() -> None:
    result = scan_controlled_sbr_instructions(_zero_operand_record(0x3D))

    assert len(result) == 1
    assert (result[0].mnemonic, result[0].selector) == ("SBR", 0x3D)
    assert result[0].operands == ()


def test_ret_differs_from_sbr_only_by_controlled_selector() -> None:
    ret = scan_controlled_ret_instructions(_zero_operand_record(0x09))[0]
    sbr = scan_controlled_sbr_instructions(_zero_operand_record(0x3D))[0]

    assert (ret.mnemonic, ret.selector) == ("RET", 0x09)
    assert (sbr.mnemonic, sbr.selector) == ("SBR", 0x3D)
    assert ret.selector_offset == sbr.selector_offset
    assert ret.operands == sbr.operands == ()


def test_mcr_differs_from_other_zero_operand_markers_by_selector() -> None:
    mcr = scan_controlled_mcr_instructions(_zero_operand_record(0x08))[0]
    ret = scan_controlled_ret_instructions(_zero_operand_record(0x09))[0]

    assert (mcr.mnemonic, mcr.selector) == ("MCR", 0x08)
    assert (ret.mnemonic, ret.selector) == ("RET", 0x09)
    assert mcr.selector_offset == ret.selector_offset
    assert mcr.operands == ret.operands == ()


def test_tnd_differs_from_other_zero_operand_markers_by_selector() -> None:
    ret = scan_controlled_ret_instructions(_zero_operand_record(0x09))[0]
    tnd = scan_controlled_tnd_instructions(_zero_operand_record(0x0B))[0]

    assert (ret.mnemonic, ret.selector) == ("RET", 0x09)
    assert (tnd.mnemonic, tnd.selector) == ("TND", 0x0B)
    assert ret.selector_offset == tnd.selector_offset
    assert ret.operands == tnd.operands == ()


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
