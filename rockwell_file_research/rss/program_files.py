"""Conservative evidence extraction from RSS ladder-program sections."""

from __future__ import annotations

import hashlib
import re
from bisect import bisect_right
from dataclasses import dataclass

from rockwell_file_research.rss.compressed_section import decompress_section
from rockwell_file_research.rss.instruction_evidence import (
    InstructionEvidence,
    scan_controlled_instructions,
)
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
    program_file_number: int | None
    program_file_name_sha256: str | None
    program_file_name: str | None
    rung_index: int | None
    rung_start_offset: int | None
    rung_end_offset: int | None


@dataclass(frozen=True)
class ProgramFileRecord:
    """One strongly delimited ladder-file header and its marker evidence."""

    marker_offset: int
    end_offset: int
    file_number: int
    header_numeric_candidate: int
    name_sha256: str
    description_sha256: str
    name: str | None
    description: str | None
    rung_reference_marker_offsets: list[int]
    declared_rung_count: int
    rung_boundaries_validated: bool
    rung_start_offsets: list[int]


@dataclass(frozen=True)
class ProgramRungRecord:
    """One corroborated rung byte range with conservative content totals."""

    program_file_number: int
    program_file_name_sha256: str
    program_file_name: str | None
    rung_index: int
    start_offset: int
    end_offset: int
    byte_length: int
    sha256: str
    operand_count: int
    direct_operand_count: int
    indirect_operand_count: int
    application_text_candidate_count: int
    application_text_candidates: list[ProgramTextRegion]


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
    instructions: list[InstructionEvidence]
    program_file_records: list[ProgramFileRecord]
    rung_records: list[ProgramRungRecord]


def _classify(text: str) -> str:
    if text in SERIALIZATION_CLASSES:
        return "serialization_class"
    if OPERAND.fullmatch(text):
        return "operand_candidate"
    return "application_text_candidate"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def scan_program_file_records(
    payload: bytes, *, include_private_text: bool = False
) -> list[ProgramFileRecord]:
    """Find observed ``03 80 ?? ?? 01 00`` ladder-file headers."""

    def decode_tail(cursor: int) -> tuple[int, str] | None:
        for optional_span in (0, 2, 4, 6):
            field_offset = cursor + optional_span
            if field_offset + 3 > len(payload):
                continue
            file_number = int.from_bytes(
                payload[field_offset : field_offset + 2], "little"
            )
            if not 2 <= file_number <= 255:
                continue
            description_length = payload[field_offset + 2]
            description_start = field_offset + 3
            description_end = description_start + description_length
            if description_end > len(payload):
                continue
            description_bytes = payload[description_start:description_end]
            if any(byte < 32 or byte > 126 for byte in description_bytes):
                continue
            return file_number, description_bytes.decode("ascii")
        return None

    candidates: list[tuple[int, int, int, str, str]] = []
    regions = inspect_processor_text(payload, include_private_text=True)
    for region in regions:
        if region.offset < 6 or region.text is None or region.length > 64:
            continue
        marker_offset = region.offset - 6
        if payload[marker_offset : marker_offset + 2] != b"\x03\x80":
            continue
        if payload[marker_offset + 4 : marker_offset + 6] != b"\x01\x00":
            continue
        # Observed names are byte-aligned: odd-length names have one padding
        # byte before the two-byte program-file number.
        cursor = region.offset + region.length + (region.length % 2)
        decoded = decode_tail(cursor)
        if decoded is None:
            continue
        file_number, description = decoded
        candidates.append(
            (
                marker_offset,
                file_number,
                int.from_bytes(
                    payload[marker_offset + 2 : marker_offset + 4], "little"
                ),
                region.text,
                description,
            )
        )
    # The shared text scanner deliberately ignores regions shorter than four
    # bytes. Apply the same header contract directly for one-to-three-byte
    # program names, then merge by byte offset.
    for marker_offset in range(max(0, len(payload) - 12)):
        if payload[marker_offset : marker_offset + 2] != b"\x03\x80":
            continue
        if payload[marker_offset + 4 : marker_offset + 6] != b"\x01\x00":
            continue
        for name_length in (1, 2, 3):
            name_start = marker_offset + 6
            name_bytes = payload[name_start : name_start + name_length]
            if len(name_bytes) != name_length or any(
                byte < 32 or byte > 126 for byte in name_bytes
            ):
                continue
            if payload[name_start + name_length] >= 32:
                continue
            cursor = name_start + name_length + (name_length % 2)
            decoded = decode_tail(cursor)
            if decoded is None:
                continue
            file_number, description = decoded
            candidates.append(
                (
                    marker_offset,
                    file_number,
                    int.from_bytes(
                        payload[marker_offset + 2 : marker_offset + 4], "little"
                    ),
                    name_bytes.decode("ascii"),
                    description,
                )
            )
            break
    candidates_by_offset: dict[int, tuple[int, int, int, str, str]] = {}
    for candidate in candidates:
        existing = candidates_by_offset.get(candidate[0])
        if existing is None or len(candidate[3]) > len(existing[3]):
            candidates_by_offset[candidate[0]] = candidate
    candidates = sorted(
        candidates_by_offset.values(), key=lambda candidate: candidate[0]
    )
    records: list[ProgramFileRecord] = []
    rung_marker = b"\x07\x80\x09\x80"
    rung_declaration = b"\xff\xff\x80\x00\x05\x00CRung"
    declaration_offset = payload.find(rung_declaration)
    for index, candidate in enumerate(candidates):
        marker_offset, file_number, numeric_candidate, name, description = candidate
        end_offset = (
            candidates[index + 1][0] if index + 1 < len(candidates) else len(payload)
        )
        rung_offsets = [
            offset
            for offset in range(marker_offset, max(marker_offset, end_offset - 3))
            if payload.startswith(rung_marker, offset)
        ]
        rung_starts = list(rung_offsets)
        if marker_offset <= declaration_offset < end_offset:
            rung_starts.insert(0, declaration_offset)
        records.append(
            ProgramFileRecord(
                marker_offset=marker_offset,
                end_offset=end_offset,
                file_number=file_number,
                header_numeric_candidate=numeric_candidate,
                name_sha256=_sha256_text(name),
                description_sha256=_sha256_text(description),
                name=name if include_private_text else None,
                description=description if include_private_text else None,
                rung_reference_marker_offsets=rung_offsets,
                declared_rung_count=numeric_candidate,
                rung_boundaries_validated=(numeric_candidate == len(rung_starts)),
                rung_start_offsets=rung_starts,
            )
        )
    return records


def inspect_program_file_section(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> ProgramFileSection:
    """Validate and catalogue program text without decoding rung opcodes."""

    section = decompress_section(payload, section_name="PROGRAM FILES")
    scanned = inspect_processor_text(section.payload, include_private_text=True)
    private_records = scan_program_file_records(
        section.payload, include_private_text=True
    )
    record_offsets = [record.marker_offset for record in private_records]
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
            record_index = bisect_right(record_offsets, region.offset) - 1
            record = private_records[record_index] if record_index >= 0 else None
            rung_index = (
                bisect_right(record.rung_start_offsets, region.offset) - 1
                if record is not None
                else -1
            )
            operands.append(
                ProgramOperand(
                    offset=region.offset,
                    length=region.length,
                    sha256=region.sha256,
                    indirect=text.startswith("#"),
                    operand=text if include_private_text else None,
                    program_file_number=(record.file_number if record else None),
                    program_file_name_sha256=(record.name_sha256 if record else None),
                    program_file_name=(
                        record.name if include_private_text and record else None
                    ),
                    rung_index=rung_index if rung_index >= 0 else None,
                    rung_start_offset=(
                        record.rung_start_offsets[rung_index]
                        if record is not None and rung_index >= 0
                        else None
                    ),
                    rung_end_offset=(
                        (
                            record.rung_start_offsets[rung_index + 1]
                            if rung_index + 1 < len(record.rung_start_offsets)
                            else record.end_offset
                        )
                        if record is not None and rung_index >= 0
                        else None
                    ),
                )
            )
    public_records = scan_program_file_records(
        section.payload,
        include_private_text=include_private_text,
    )
    rung_records: list[ProgramRungRecord] = []
    for record in public_records:
        if not record.rung_boundaries_validated:
            continue
        for rung_index, start_offset in enumerate(record.rung_start_offsets):
            end_offset = (
                record.rung_start_offsets[rung_index + 1]
                if rung_index + 1 < len(record.rung_start_offsets)
                else record.end_offset
            )
            rung_operands = [
                operand
                for operand in operands
                if operand.program_file_number == record.file_number
                and operand.rung_index == rung_index
            ]
            rung_text_candidates = [
                region
                for region in text_regions
                if region.classification == "application_text_candidate"
                and start_offset <= region.offset < end_offset
            ]
            rung_records.append(
                ProgramRungRecord(
                    program_file_number=record.file_number,
                    program_file_name_sha256=record.name_sha256,
                    program_file_name=record.name,
                    rung_index=rung_index,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    byte_length=end_offset - start_offset,
                    sha256=hashlib.sha256(
                        section.payload[start_offset:end_offset]
                    ).hexdigest(),
                    operand_count=len(rung_operands),
                    direct_operand_count=sum(
                        not operand.indirect for operand in rung_operands
                    ),
                    indirect_operand_count=sum(
                        operand.indirect for operand in rung_operands
                    ),
                    application_text_candidate_count=len(rung_text_candidates),
                    application_text_candidates=rung_text_candidates,
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
        instructions=scan_controlled_instructions(
            section.payload,
            include_private_text=include_private_text,
        ),
        program_file_records=public_records,
        rung_records=rung_records,
    )
