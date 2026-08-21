"""Evidence-backed recognition of controlled RSS instruction records."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_CONTROLLED_SIMPLE_BIT_SELECTORS = {
    0x2F: "OTE",
    0x30: "OTL",
    0x31: "OTU",
    0x39: "XIC",
    0x3A: "XIO",
}
_CONTROLLED_BIT_OPERAND = re.compile(r"^B\d+:\d+/\d+$", re.IGNORECASE)
_CONTROLLED_WORD_OPERAND = re.compile(r"^N\d+:\d+$", re.IGNORECASE)
_CONTROLLED_FILE_WORD_OPERAND = re.compile(r"^#N\d+:\d+$", re.IGNORECASE)
_CONTROLLED_CONTROL_OPERAND = re.compile(r"^R\d+:\d+$", re.IGNORECASE)
_CONTROLLED_TIMER_OPERAND = re.compile(r"^T\d+:\d+$", re.IGNORECASE)
_CONTROLLED_RESET_OPERAND = re.compile(r"^[TC]\d+:\d+$", re.IGNORECASE)
_CONTROLLED_INTEGER = re.compile(r"^\d+$")
_SIMPLE_BIT_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/simple-bit/v1"
_MOV_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/mov/v1"
_NEG_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/neg/v1"
_SQR_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/sqr/v1"
_ABS_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/abs/v1"
_NOT_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/not/v1"
_EQU_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/equ/v1"
_NEQ_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/neq/v1"
_LES_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/les/v1"
_LEQ_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/leq/v1"
_GRT_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/grt/v1"
_GEQ_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/geq/v1"
_MEQ_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/meq/v1"
_LIM_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/lim/v1"
_SCP_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/scp/v1"
_SCL_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/scl/v1"
_SWP_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/swp/v1"
_COP_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/cop/v1"
_FLL_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/fll/v1"
_FFL_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/ffl/v1"
_FFU_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/ffu/v1"
_LFL_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/lfl/v1"
_TOD_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/tod/v1"
_FRD_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/frd/v1"
_AND_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/and/v1"
_OR_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/or/v1"
_XOR_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/xor/v1"
_CLR_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/clr/v1"
_ADD_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/add/v1"
_SUB_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/sub/v1"
_MUL_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/mul/v1"
_DIV_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/div/v1"
_TON_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/ton/v1"
_RTO_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/rto/v1"
_TOF_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/tof/v1"
_RES_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/res/v1"
_CTU_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/ctu/v1"
_CTD_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/ctd/v1"
_COUNTER_IDENTITIES = {
    0x11: ("CTU", _CTU_PROFILE),
    0x12: ("CTD", _CTD_PROFILE),
}
_TIMER_IDENTITIES = {
    0xA7: ("TON", _TON_PROFILE),
    0xA3: ("RTO", _RTO_PROFILE),
    0xA6: ("TOF", _TOF_PROFILE),
}
_FILE_OPERATION_IDENTITIES = {
    0x41: (
        "FFL",
        _FFL_PROFILE,
        ("source", "fifo", "control", "length", "position"),
        (
            _CONTROLLED_WORD_OPERAND,
            _CONTROLLED_FILE_WORD_OPERAND,
            _CONTROLLED_CONTROL_OPERAND,
            _CONTROLLED_INTEGER,
            _CONTROLLED_INTEGER,
        ),
        0x05,
    ),
    0x42: (
        "FFU",
        _FFU_PROFILE,
        ("fifo", "destination", "control", "length", "position"),
        (
            _CONTROLLED_FILE_WORD_OPERAND,
            _CONTROLLED_WORD_OPERAND,
            _CONTROLLED_CONTROL_OPERAND,
            _CONTROLLED_INTEGER,
            _CONTROLLED_INTEGER,
        ),
        0x05,
    ),
    0x43: (
        "LFL",
        _LFL_PROFILE,
        ("source", "lifo", "control", "length", "position"),
        (
            _CONTROLLED_WORD_OPERAND,
            _CONTROLLED_FILE_WORD_OPERAND,
            _CONTROLLED_CONTROL_OPERAND,
            _CONTROLLED_INTEGER,
            _CONTROLLED_INTEGER,
        ),
        0x05,
    ),
    0x21: (
        "FLL",
        _FLL_PROFILE,
        ("source", "destination", "length"),
        (
            _CONTROLLED_WORD_OPERAND,
            _CONTROLLED_FILE_WORD_OPERAND,
            _CONTROLLED_INTEGER,
        ),
        0x03,
    ),
    0x22: (
        "COP",
        _COP_PROFILE,
        ("source", "destination", "length"),
        (
            _CONTROLLED_FILE_WORD_OPERAND,
            _CONTROLLED_FILE_WORD_OPERAND,
            _CONTROLLED_INTEGER,
        ),
        0x03,
    ),
    0x96: (
        "SWP",
        _SWP_PROFILE,
        ("source", "length"),
        (_CONTROLLED_FILE_WORD_OPERAND, _CONTROLLED_INTEGER),
        0x02,
    ),
}
_QUALIFIED_WORD_IDENTITIES = {
    0x14: ("CLR", _CLR_PROFILE, ("destination",), 0x02),
    0x17: ("TOD", _TOD_PROFILE, ("source", "destination"), 0x04),
    0x18: ("FRD", _FRD_PROFILE, ("source", "destination"), 0x04),
    0x1B: ("NOT", _NOT_PROFILE, ("source", "destination"), 0x04),
    0x1C: ("MOV", _MOV_PROFILE, ("source", "destination"), 0x04),
    0x1E: ("NEG", _NEG_PROFILE, ("source", "destination"), 0x04),
    0x23: (
        "AND",
        _AND_PROFILE,
        ("source_a", "source_b", "destination"),
        0x06,
    ),
    0x24: (
        "OR",
        _OR_PROFILE,
        ("source_a", "source_b", "destination"),
        0x06,
    ),
    0x25: (
        "XOR",
        _XOR_PROFILE,
        ("source_a", "source_b", "destination"),
        0x06,
    ),
    0x27: (
        "ADD",
        _ADD_PROFILE,
        ("source_a", "source_b", "destination"),
        0x06,
    ),
    0x28: (
        "SUB",
        _SUB_PROFILE,
        ("source_a", "source_b", "destination"),
        0x06,
    ),
    0x29: (
        "MUL",
        _MUL_PROFILE,
        ("source_a", "source_b", "destination"),
        0x06,
    ),
    0x2A: (
        "DIV",
        _DIV_PROFILE,
        ("source_a", "source_b", "destination"),
        0x06,
    ),
    0x32: ("EQU", _EQU_PROFILE, ("source_a", "source_b"), 0x04),
    0x33: ("NEQ", _NEQ_PROFILE, ("source_a", "source_b"), 0x04),
    0x34: ("GRT", _GRT_PROFILE, ("source_a", "source_b"), 0x04),
    0x35: ("GEQ", _GEQ_PROFILE, ("source_a", "source_b"), 0x04),
    0x36: ("LES", _LES_PROFILE, ("source_a", "source_b"), 0x04),
    0x37: ("LEQ", _LEQ_PROFILE, ("source_a", "source_b"), 0x04),
    0x38: ("MEQ", _MEQ_PROFILE, ("source", "mask", "compare"), 0x06),
    0x3F: ("LIM", _LIM_PROFILE, ("low_limit", "test", "high_limit"), 0x06),
    0x45: (
        "SCL",
        _SCL_PROFILE,
        ("source", "rate", "offset", "destination"),
        0x08,
    ),
    0x95: (
        "SCP",
        _SCP_PROFILE,
        (
            "input",
            "input_min",
            "input_max",
            "scaled_min",
            "scaled_max",
            "output",
        ),
        0x0C,
    ),
    0x46: ("SQR", _SQR_PROFILE, ("source", "destination"), 0x04),
    0x98: ("ABS", _ABS_PROFILE, ("source", "destination"), 0x04),
}


@dataclass(frozen=True)
class InstructionOperandEvidence:
    """One ordered instruction operand with an evidence-backed role."""

    role: str
    offset: int
    length: int
    sha256: str
    value: str | None


@dataclass(frozen=True)
class InstructionEvidence:
    """One instruction identity supported by a controlled record profile."""

    mnemonic: str
    selector: int
    selector_offset: int
    operands: tuple[InstructionOperandEvidence, ...]
    evidence_profile: str


def _operand(
    *,
    role: str,
    offset: int,
    value: bytes,
    include_private_text: bool,
) -> InstructionOperandEvidence:
    decoded = value.decode("ascii")
    return InstructionOperandEvidence(
        role=role,
        offset=offset,
        length=len(value),
        sha256=hashlib.sha256(value).hexdigest(),
        value=decoded if include_private_text else None,
    )


def scan_controlled_simple_bit_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize only records matching the controlled simple-bit profile.

    The selector values are not treated as global opcodes. Recognition also
    requires the length-prefixed ``B`` bit operand and the invariant bytes
    observed across the controlled XIC, XIO, OTE, OTL, and OTU fixtures.
    """

    evidence: list[InstructionEvidence] = []
    for operand_offset in range(3, len(payload)):
        operand_length = payload[operand_offset - 1]
        if not operand_length or operand_offset + operand_length + 9 > len(payload):
            continue
        if payload[operand_offset - 3 : operand_offset - 1] != b"\x01\x00":
            continue
        operand_bytes = payload[operand_offset : operand_offset + operand_length]
        try:
            operand = operand_bytes.decode("ascii")
        except UnicodeDecodeError:
            continue
        if _CONTROLLED_BIT_OPERAND.fullmatch(operand) is None:
            continue
        selector_offset = operand_offset + operand_length + 2
        if payload[operand_offset + operand_length : selector_offset] != b"\x00\x00":
            continue
        selector = payload[selector_offset]
        mnemonic = _CONTROLLED_SIMPLE_BIT_SELECTORS.get(selector)
        if mnemonic is None:
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        evidence.append(
            InstructionEvidence(
                mnemonic=mnemonic,
                selector=selector,
                selector_offset=selector_offset,
                operands=(
                    _operand(
                        role="operand",
                        offset=operand_offset,
                        value=operand_bytes,
                        include_private_text=include_private_text,
                    ),
                ),
                evidence_profile=_SIMPLE_BIT_PROFILE,
            )
        )
    return evidence


def _scan_controlled_qualified_word_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize controlled qualified-word instruction records."""

    evidence: list[InstructionEvidence] = []
    for record_offset in range(max(0, len(payload) - 1)):
        header_value = payload[record_offset]
        if payload[record_offset + 1] != 0 or header_value not in {
            0x02,
            0x04,
            0x06,
            0x08,
            0x0C,
        }:
            continue
        cursor = record_offset + 2
        fields: list[tuple[int, bytes]] = []
        for _ in range(header_value // 2):
            if cursor >= len(payload):
                break
            length = payload[cursor]
            offset = cursor + 1
            end = offset + length
            if not length or end + 2 > len(payload):
                break
            value = payload[offset:end]
            if payload[end : end + 2] != b"\x01\x3f":
                break
            fields.append((offset, value))
            cursor = end + 2
        if len(fields) != header_value // 2 or cursor + 10 > len(payload):
            continue
        if payload[cursor : cursor + 2] != b"\x00\x00":
            continue
        selector_offset = cursor + 2
        selector = payload[selector_offset]
        identity = _QUALIFIED_WORD_IDENTITIES.get(selector)
        if identity is None:
            continue
        mnemonic, profile, roles, expected_header = identity
        if header_value != expected_header or len(fields) != len(roles):
            continue
        try:
            decoded = [value.decode("ascii") for _, value in fields]
        except UnicodeDecodeError:
            continue
        if any(_CONTROLLED_WORD_OPERAND.fullmatch(value) is None for value in decoded):
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        evidence.append(
            InstructionEvidence(
                mnemonic=mnemonic,
                selector=selector,
                selector_offset=selector_offset,
                operands=tuple(
                    _operand(
                        role=role,
                        offset=offset,
                        value=value,
                        include_private_text=include_private_text,
                    )
                    for role, (offset, value) in zip(roles, fields, strict=True)
                ),
                evidence_profile=profile,
            )
        )
    return evidence


def scan_controlled_mov_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize MOV records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "MOV"
    ]


def scan_controlled_clr_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize CLR records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "CLR"
    ]


def scan_controlled_neg_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize NEG records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "NEG"
    ]


def scan_controlled_sqr_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize SQR records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "SQR"
    ]


def scan_controlled_abs_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize ABS records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "ABS"
    ]


def scan_controlled_not_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize NOT records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "NOT"
    ]


def scan_controlled_equ_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize EQU records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "EQU"
    ]


def scan_controlled_neq_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize NEQ records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "NEQ"
    ]


def scan_controlled_les_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize LES records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "LES"
    ]


def scan_controlled_leq_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize LEQ records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "LEQ"
    ]


def scan_controlled_grt_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize GRT records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "GRT"
    ]


def scan_controlled_geq_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize GEQ records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "GEQ"
    ]


def scan_controlled_meq_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize MEQ records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "MEQ"
    ]


def scan_controlled_lim_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize LIM records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "LIM"
    ]


def scan_controlled_scp_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize SCP records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "SCP"
    ]


def scan_controlled_scl_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize SCL records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "SCL"
    ]


def _scan_controlled_file_operation_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize controlled file operations with unqualified fields."""

    evidence: list[InstructionEvidence] = []
    for record_offset in range(max(0, len(payload) - 1)):
        field_count = payload[record_offset]
        if payload[record_offset + 1] != 0 or field_count not in {2, 3, 5}:
            continue
        cursor = record_offset + 2
        fields: list[tuple[int, bytes]] = []
        for _ in range(field_count):
            if cursor >= len(payload):
                break
            length = payload[cursor]
            offset = cursor + 1
            end = offset + length
            if not length or end > len(payload):
                break
            fields.append((offset, payload[offset:end]))
            cursor = end
        if len(fields) != field_count or cursor + 10 > len(payload):
            continue
        if payload[cursor : cursor + 2] != b"\x00\x00":
            continue
        selector_offset = cursor + 2
        selector = payload[selector_offset]
        identity = _FILE_OPERATION_IDENTITIES.get(selector)
        if identity is None:
            continue
        mnemonic, profile, roles, patterns, expected_count = identity
        if field_count != expected_count:
            continue
        try:
            decoded = [value.decode("ascii") for _, value in fields]
        except UnicodeDecodeError:
            continue
        if any(
            pattern.fullmatch(value) is None
            for pattern, value in zip(patterns, decoded, strict=True)
        ):
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        evidence.append(
            InstructionEvidence(
                mnemonic=mnemonic,
                selector=selector,
                selector_offset=selector_offset,
                operands=tuple(
                    _operand(
                        role=role,
                        offset=offset,
                        value=value,
                        include_private_text=include_private_text,
                    )
                    for role, (offset, value) in zip(roles, fields, strict=True)
                ),
                evidence_profile=profile,
            )
        )
    return evidence


def scan_controlled_swp_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize SWP records matching the controlled file-operation profile."""

    return [
        item
        for item in _scan_controlled_file_operation_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "SWP"
    ]


def scan_controlled_cop_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize COP records matching the controlled file-operation profile."""

    return [
        item
        for item in _scan_controlled_file_operation_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "COP"
    ]


def scan_controlled_fll_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize FLL records matching the controlled file-operation profile."""

    return [
        item
        for item in _scan_controlled_file_operation_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "FLL"
    ]


def scan_controlled_ffl_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize FFL records matching the controlled file-operation profile."""

    return [
        item
        for item in _scan_controlled_file_operation_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "FFL"
    ]


def scan_controlled_ffu_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize FFU records matching the controlled file-operation profile."""

    return [
        item
        for item in _scan_controlled_file_operation_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "FFU"
    ]


def scan_controlled_lfl_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize LFL records matching the controlled file-operation profile."""

    return [
        item
        for item in _scan_controlled_file_operation_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "LFL"
    ]


def scan_controlled_tod_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize TOD records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "TOD"
    ]


def scan_controlled_frd_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize FRD records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "FRD"
    ]


def scan_controlled_and_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize AND records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "AND"
    ]


def scan_controlled_or_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize OR records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "OR"
    ]


def scan_controlled_xor_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize XOR records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "XOR"
    ]


def scan_controlled_add_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize ADD records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "ADD"
    ]


def scan_controlled_sub_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize SUB records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "SUB"
    ]


def scan_controlled_mul_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize MUL records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "MUL"
    ]


def scan_controlled_div_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize DIV records matching the controlled qualified-word profile."""

    return [
        item
        for item in _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "DIV"
    ]


def _scan_controlled_timer_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize controlled TON and RTO four-field records."""

    evidence: list[InstructionEvidence] = []
    for record_offset in range(max(0, len(payload) - 24)):
        if payload[record_offset : record_offset + 2] != b"\x04\x00":
            continue
        cursor = record_offset + 2
        fields: list[tuple[int, bytes]] = []
        for _ in range(4):
            if cursor >= len(payload):
                break
            length = payload[cursor]
            offset = cursor + 1
            end = offset + length
            if not length or end > len(payload):
                break
            fields.append((offset, payload[offset:end]))
            cursor = end
        if len(fields) != 4 or cursor + 10 > len(payload):
            continue
        try:
            timer, time_base, preset, accumulator = (
                value.decode("ascii") for _, value in fields
            )
        except UnicodeDecodeError:
            continue
        if _CONTROLLED_TIMER_OPERAND.fullmatch(timer) is None:
            continue
        if time_base != "1.0":
            continue
        if _CONTROLLED_INTEGER.fullmatch(preset) is None or accumulator != "0":
            continue
        if payload[cursor : cursor + 2] != b"\x00\x00":
            continue
        selector_offset = cursor + 2
        selector = payload[selector_offset]
        identity = _TIMER_IDENTITIES.get(selector)
        if identity is None:
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        roles = ("timer", "time_base", "preset", "accumulator")
        mnemonic, profile = identity
        evidence.append(
            InstructionEvidence(
                mnemonic=mnemonic,
                selector=selector,
                selector_offset=selector_offset,
                operands=tuple(
                    _operand(
                        role=role,
                        offset=offset,
                        value=value,
                        include_private_text=include_private_text,
                    )
                    for role, (offset, value) in zip(roles, fields, strict=True)
                ),
                evidence_profile=profile,
            )
        )
    return evidence


def scan_controlled_ton_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize TON records matching the controlled timer profile."""

    return [
        item
        for item in _scan_controlled_timer_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "TON"
    ]


def scan_controlled_rto_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize RTO records matching the controlled timer profile."""

    return [
        item
        for item in _scan_controlled_timer_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "RTO"
    ]


def scan_controlled_tof_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize TOF records matching the controlled timer profile."""

    return [
        item
        for item in _scan_controlled_timer_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "TOF"
    ]


def scan_controlled_res_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize RES records for controlled timer and counter operands."""

    evidence: list[InstructionEvidence] = []
    for operand_offset in range(3, len(payload)):
        operand_length = payload[operand_offset - 1]
        if not operand_length or operand_offset + operand_length + 9 > len(payload):
            continue
        if payload[operand_offset - 3 : operand_offset - 1] != b"\x01\x00":
            continue
        operand_bytes = payload[operand_offset : operand_offset + operand_length]
        try:
            operand = operand_bytes.decode("ascii")
        except UnicodeDecodeError:
            continue
        if _CONTROLLED_RESET_OPERAND.fullmatch(operand) is None:
            continue
        selector_offset = operand_offset + operand_length + 2
        if payload[operand_offset + operand_length : selector_offset] != b"\x00\x00":
            continue
        if payload[selector_offset] != 0x13:
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        evidence.append(
            InstructionEvidence(
                mnemonic="RES",
                selector=0x13,
                selector_offset=selector_offset,
                operands=(
                    _operand(
                        role="operand",
                        offset=operand_offset,
                        value=operand_bytes,
                        include_private_text=include_private_text,
                    ),
                ),
                evidence_profile=_RES_PROFILE,
            )
        )
    return evidence


def _scan_controlled_counter_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize controlled CTU and CTD three-field records."""

    evidence: list[InstructionEvidence] = []
    for record_offset in range(max(0, len(payload) - 20)):
        if payload[record_offset : record_offset + 2] != b"\x03\x00":
            continue
        cursor = record_offset + 2
        fields: list[tuple[int, bytes]] = []
        for _ in range(3):
            if cursor >= len(payload):
                break
            length = payload[cursor]
            offset = cursor + 1
            end = offset + length
            if not length or end > len(payload):
                break
            fields.append((offset, payload[offset:end]))
            cursor = end
        if len(fields) != 3 or cursor + 10 > len(payload):
            continue
        try:
            counter, preset, accumulator = (
                value.decode("ascii") for _, value in fields
            )
        except UnicodeDecodeError:
            continue
        if re.fullmatch(r"C\d+:\d+", counter, re.IGNORECASE) is None:
            continue
        if _CONTROLLED_INTEGER.fullmatch(preset) is None or accumulator != "0":
            continue
        if payload[cursor : cursor + 2] != b"\x00\x00":
            continue
        selector_offset = cursor + 2
        selector = payload[selector_offset]
        identity = _COUNTER_IDENTITIES.get(selector)
        if identity is None:
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        roles = ("counter", "preset", "accumulator")
        mnemonic, profile = identity
        evidence.append(
            InstructionEvidence(
                mnemonic=mnemonic,
                selector=selector,
                selector_offset=selector_offset,
                operands=tuple(
                    _operand(
                        role=role,
                        offset=offset,
                        value=value,
                        include_private_text=include_private_text,
                    )
                    for role, (offset, value) in zip(roles, fields, strict=True)
                ),
                evidence_profile=profile,
            )
        )
    return evidence


def scan_controlled_ctu_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize CTU records matching the controlled counter profile."""

    return [
        item
        for item in _scan_controlled_counter_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "CTU"
    ]


def scan_controlled_ctd_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize CTD records matching the controlled counter profile."""

    return [
        item
        for item in _scan_controlled_counter_instructions(
            payload,
            include_private_text=include_private_text,
        )
        if item.mnemonic == "CTD"
    ]


def scan_controlled_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize every implemented controlled profile in source byte order."""

    evidence = scan_controlled_simple_bit_instructions(
        payload,
        include_private_text=include_private_text,
    )
    evidence.extend(
        _scan_controlled_qualified_word_instructions(
            payload,
            include_private_text=include_private_text,
        )
    )
    evidence.extend(
        _scan_controlled_timer_instructions(
            payload,
            include_private_text=include_private_text,
        )
    )
    evidence.extend(
        _scan_controlled_file_operation_instructions(
            payload,
            include_private_text=include_private_text,
        )
    )
    evidence.extend(
        scan_controlled_res_instructions(
            payload,
            include_private_text=include_private_text,
        )
    )
    evidence.extend(
        _scan_controlled_counter_instructions(
            payload,
            include_private_text=include_private_text,
        )
    )
    return sorted(evidence, key=lambda item: item.selector_offset)
