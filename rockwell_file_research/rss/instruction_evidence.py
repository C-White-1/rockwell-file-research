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
_CONTROLLED_TIMER_OPERAND = re.compile(r"^T\d+:\d+$", re.IGNORECASE)
_CONTROLLED_RESET_OPERAND = re.compile(r"^[TC]\d+:\d+$", re.IGNORECASE)
_CONTROLLED_INTEGER = re.compile(r"^\d+$")
_SIMPLE_BIT_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/simple-bit/v1"
_MOV_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/mov/v1"
_TON_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/ton/v1"
_RES_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/res/v1"


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


def scan_controlled_mov_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize MOV records matching the controlled two-word profile."""

    evidence: list[InstructionEvidence] = []
    for record_offset in range(max(0, len(payload) - 20)):
        if payload[record_offset : record_offset + 2] != b"\x04\x00":
            continue
        source_length = payload[record_offset + 2]
        source_offset = record_offset + 3
        source_end = source_offset + source_length
        if source_end + 3 >= len(payload):
            continue
        source_bytes = payload[source_offset:source_end]
        if payload[source_end : source_end + 2] != b"\x01\x3f":
            continue
        destination_length_offset = source_end + 2
        destination_length = payload[destination_length_offset]
        destination_offset = destination_length_offset + 1
        destination_end = destination_offset + destination_length
        if destination_end + 11 > len(payload):
            continue
        destination_bytes = payload[destination_offset:destination_end]
        try:
            source = source_bytes.decode("ascii")
            destination = destination_bytes.decode("ascii")
        except UnicodeDecodeError:
            continue
        if (
            _CONTROLLED_WORD_OPERAND.fullmatch(source) is None
            or _CONTROLLED_WORD_OPERAND.fullmatch(destination) is None
        ):
            continue
        selector_offset = destination_end + 4
        if payload[destination_end:selector_offset] != b"\x01\x3f\x00\x00":
            continue
        if payload[selector_offset] != 0x1C:
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        evidence.append(
            InstructionEvidence(
                mnemonic="MOV",
                selector=0x1C,
                selector_offset=selector_offset,
                operands=(
                    _operand(
                        role="source",
                        offset=source_offset,
                        value=source_bytes,
                        include_private_text=include_private_text,
                    ),
                    _operand(
                        role="destination",
                        offset=destination_offset,
                        value=destination_bytes,
                        include_private_text=include_private_text,
                    ),
                ),
                evidence_profile=_MOV_PROFILE,
            )
        )
    return evidence


def scan_controlled_ton_instructions(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[InstructionEvidence]:
    """Recognize TON records matching the controlled four-field profile."""

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
        if payload[selector_offset] != 0xA7:
            continue
        if payload[selector_offset + 1 : selector_offset + 8] != (
            b"\x00\x00\x00\x00\x00\x0b\x80"
        ):
            continue
        roles = ("timer", "time_base", "preset", "accumulator")
        evidence.append(
            InstructionEvidence(
                mnemonic="TON",
                selector=0xA7,
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
                evidence_profile=_TON_PROFILE,
            )
        )
    return evidence


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
        scan_controlled_mov_instructions(
            payload,
            include_private_text=include_private_text,
        )
    )
    evidence.extend(
        scan_controlled_ton_instructions(
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
    return sorted(evidence, key=lambda item: item.selector_offset)
