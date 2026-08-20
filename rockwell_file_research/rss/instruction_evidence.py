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
_PROFILE = "rslogix-micro-starter-lite/ml1100-series-b/simple-bit/v1"


@dataclass(frozen=True)
class InstructionEvidence:
    """One instruction identity supported by a controlled record profile."""

    mnemonic: str
    selector: int
    selector_offset: int
    operand_offset: int
    operand_length: int
    operand_sha256: str
    operand: str | None
    evidence_profile: str


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
                operand_offset=operand_offset,
                operand_length=operand_length,
                operand_sha256=hashlib.sha256(operand_bytes).hexdigest(),
                operand=operand if include_private_text else None,
                evidence_profile=_PROFILE,
            )
        )
    return evidence
