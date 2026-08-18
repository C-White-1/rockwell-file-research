"""Conservative evidence extraction from RSS data-file sections."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from rockwell_file_research.rss.compressed_section import decompress_section
from rockwell_file_research.rss.processor import inspect_processor_text

STANDARD_DATA_FILE_LABELS = frozenset(
    {
        "BINARY",
        "CONTROL",
        "COUNTER",
        "FLOAT",
        "INPUT",
        "INTEGER",
        "OUTPUT",
        "PID",
        "STATUS",
        "STRING",
        "TIMER",
    }
)
SERIALIZATION_CLASSES = frozenset({"CDataFile", "CDataHolder", "CSlcMDataFile"})


@dataclass(frozen=True)
class DataFileTextRegion:
    """One printable region from an uncompressed data-file section."""

    classification: str
    offset: int
    length: int
    sha256: str
    text: str | None


@dataclass(frozen=True)
class DataFileRecord:
    """One strongly delimited, but not yet fully decoded, data-file record."""

    offset: int
    file_number: int
    description: str
    name: str
    description_sha256: str
    name_sha256: str
    element_count_candidate: int
    marker_offset: int


@dataclass(frozen=True)
class DataFileSection:
    """Verified compression and redacted text evidence for one section."""

    envelope_version: int
    header_size: int
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    text_regions: list[DataFileTextRegion]
    records: list[DataFileRecord]


def _classify(text: str | None) -> str:
    if text in SERIALIZATION_CLASSES:
        return "serialization_class"
    if text in STANDARD_DATA_FILE_LABELS:
        return "standard_data_file_label"
    return "application_text_candidate"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def scan_data_file_records(payload: bytes) -> list[DataFileRecord]:
    """Find records using length prefixes and the observed ``03 80`` marker."""

    records: list[DataFileRecord] = []
    for offset in range(max(0, len(payload) - 24)):
        file_number = int.from_bytes(payload[offset : offset + 2], "little")
        description_length = payload[offset + 2]
        if file_number > 255 or description_length > 120:
            continue
        description_start = offset + 3
        description_end = description_start + description_length
        if description_end >= len(payload):
            continue
        name_length = payload[description_end]
        if not 1 <= name_length <= 64:
            continue
        name_start = description_end + 1
        name_end = name_start + name_length
        if name_end + 16 > len(payload) or payload[name_end : name_end + 4] != bytes(4):
            continue
        description_bytes = payload[description_start:description_end]
        name_bytes = payload[name_start:name_end]
        if any(byte < 32 or byte > 126 for byte in description_bytes + name_bytes):
            continue
        marker_offset = -1
        marker_limit = min(name_end + 18, len(payload) - 11)
        for candidate in range(name_end + 4, marker_limit, 2):
            if payload[candidate : candidate + 2] == b"\x03\x80":
                marker_offset = candidate
                break
        if marker_offset < 0:
            continue
        description = description_bytes.decode("ascii")
        name = name_bytes.decode("ascii")
        records.append(
            DataFileRecord(
                offset=offset,
                file_number=file_number,
                description=description,
                name=name,
                description_sha256=_sha256_text(description),
                name_sha256=_sha256_text(name),
                element_count_candidate=int.from_bytes(
                    payload[marker_offset + 10 : marker_offset + 12], "little"
                ),
                marker_offset=marker_offset,
            )
        )
    return records


def inspect_data_file_section(
    payload: bytes,
    *,
    section_name: str,
    include_private_text: bool = False,
) -> DataFileSection:
    """Verify compression and catalogue text without interpreting values."""

    section = decompress_section(payload, section_name=section_name)
    scanned = inspect_processor_text(section.payload, include_private_text=True)
    regions = [
        DataFileTextRegion(
            classification=_classify(region.text),
            offset=region.offset,
            length=region.length,
            sha256=region.sha256,
            text=region.text if include_private_text else None,
        )
        for region in scanned
    ]
    records = scan_data_file_records(section.payload)
    return DataFileSection(
        envelope_version=section.envelope_version,
        header_size=section.header_size,
        compressed_size=section.compressed_size,
        uncompressed_size=section.uncompressed_size,
        compressed_sha256=section.compressed_sha256,
        uncompressed_sha256=section.uncompressed_sha256,
        text_regions=regions,
        records=records,
    )
