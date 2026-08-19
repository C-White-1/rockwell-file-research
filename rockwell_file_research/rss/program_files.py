"""Conservative evidence extraction from RSS ladder-program sections."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rockwell_file_research.rss.compressed_section import decompress_section
from rockwell_file_research.rss.processor import inspect_processor_text

SERIALIZATION_CLASSES = frozenset(
    {"CProgHolder", "CLadFile", "CRung", "CBranchLeg", "CIns", "CBranch"}
)
OPERAND = re.compile(
    r"^#?[A-Za-z]+(?:\d+)?(?::|/)[A-Za-z0-9.:/#]+$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProgramTextRegion:
    """One classified printable region in a ladder-program payload."""

    classification: str
    offset: int
    length: int
    sha256: str
    text: str | None


@dataclass(frozen=True)
class ProgramOperand:
    """One direct or indirect operand string with byte provenance."""

    offset: int
    length: int
    sha256: str
    indirect: bool
    operand: str | None


@dataclass(frozen=True)
class ProgramFileSection:
    """Validated compression and text evidence for RSS PROGRAM FILES."""

    envelope_version: int
    header_size: int
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    text_regions: list[ProgramTextRegion]
    operands: list[ProgramOperand]


def _classify(text: str) -> str:
    if text in SERIALIZATION_CLASSES:
        return "serialization_class"
    if OPERAND.fullmatch(text):
        return "operand_candidate"
    return "application_text_candidate"


def inspect_program_file_section(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> ProgramFileSection:
    """Validate and catalogue program text without decoding rung opcodes."""

    section = decompress_section(payload, section_name="PROGRAM FILES")
    scanned = inspect_processor_text(section.payload, include_private_text=True)
    text_regions: list[ProgramTextRegion] = []
    operands: list[ProgramOperand] = []
    for region in scanned:
        text = region.text or ""
        classification = _classify(text)
        text_regions.append(
            ProgramTextRegion(
                classification=classification,
                offset=region.offset,
                length=region.length,
                sha256=region.sha256,
                text=text if include_private_text else None,
            )
        )
        if classification == "operand_candidate":
            operands.append(
                ProgramOperand(
                    offset=region.offset,
                    length=region.length,
                    sha256=region.sha256,
                    indirect=text.startswith("#"),
                    operand=text if include_private_text else None,
                )
            )
    return ProgramFileSection(
        envelope_version=section.envelope_version,
        header_size=section.header_size,
        compressed_size=section.compressed_size,
        uncompressed_size=section.uncompressed_size,
        compressed_sha256=section.compressed_sha256,
        uncompressed_sha256=section.uncompressed_sha256,
        text_regions=text_regions,
        operands=operands,
    )
