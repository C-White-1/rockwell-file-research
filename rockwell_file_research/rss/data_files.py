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
INTEGER_TYPE_MARKER = bytes.fromhex("03 80 07")
BINARY_TYPE_MARKER = bytes.fromhex("03 80 03")
INTEGER_HEADER_SUFFIX = bytes.fromhex("01 00 00 00 FF FF")


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
    unknown_numeric_candidate: int
    marker_offset: int


@dataclass(frozen=True)
class IntegerDataFileValues:
    """Signed 16-bit values with structural byte provenance."""

    file_number: int
    header_offset: int
    values_offset: int
    element_count: int
    values_sha256: str
    values: tuple[int, ...]


@dataclass(frozen=True)
class BinaryDataFileWords:
    """Unsigned 16-bit binary words with structural byte provenance."""

    file_number: int
    header_offset: int
    values_offset: int
    element_count: int
    values_sha256: str
    words: tuple[int, ...]


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
    integer_values: list[IntegerDataFileValues]
    binary_words: list[BinaryDataFileWords]


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
                unknown_numeric_candidate=int.from_bytes(
                    payload[marker_offset + 10 : marker_offset + 12], "little"
                ),
                marker_offset=marker_offset,
            )
        )
    return records


def scan_integer_data_file_values(
    payload: bytes,
    records: list[DataFileRecord] | None = None,
) -> list[IntegerDataFileValues]:
    """Decode structurally delimited signed 16-bit integer value arrays.

    Controlled MicroLogix fixtures established the integer type marker, the
    element-count header, a two-byte little-endian stride, and adjacency of the
    value array to its catalogue record. Records that do not satisfy every
    invariant remain uninterpreted.
    """

    candidates = records if records is not None else scan_data_file_records(payload)
    decoded: list[IntegerDataFileValues] = []
    for record in candidates:
        matches: list[IntegerDataFileValues] = []
        suffix_offset = payload.find(INTEGER_HEADER_SUFFIX, 0, record.offset)
        while suffix_offset >= 2:
            header_offset = suffix_offset - 2
            element_count = int.from_bytes(
                payload[header_offset : header_offset + 2], "little"
            )
            values_offset = header_offset + 8
            values_end = values_offset + element_count * 2
            marker_offset = payload.rfind(
                INTEGER_TYPE_MARKER,
                max(0, header_offset - 32),
                header_offset,
            )
            if element_count > 0 and values_end == record.offset and marker_offset >= 0:
                value_bytes = payload[values_offset:values_end]
                matches.append(
                    IntegerDataFileValues(
                        file_number=record.file_number,
                        header_offset=header_offset,
                        values_offset=values_offset,
                        element_count=element_count,
                        values_sha256=hashlib.sha256(value_bytes).hexdigest(),
                        values=tuple(
                            int.from_bytes(
                                value_bytes[offset : offset + 2],
                                "little",
                                signed=True,
                            )
                            for offset in range(0, len(value_bytes), 2)
                        ),
                    )
                )
            suffix_offset = payload.find(
                INTEGER_HEADER_SUFFIX,
                suffix_offset + 1,
                record.offset,
            )
        if len(matches) == 1:
            decoded.append(matches[0])
    return decoded


def scan_binary_data_file_words(
    payload: bytes,
    records: list[DataFileRecord] | None = None,
) -> list[BinaryDataFileWords]:
    """Decode structurally delimited unsigned 16-bit binary word arrays.

    Controlled B10 fixtures established the binary type marker, element-count
    header, little-endian word stride, bit numbering, and exact adjacency to
    the catalogue record. Ambiguous records remain uninterpreted.
    """

    candidates = records if records is not None else scan_data_file_records(payload)
    decoded: list[BinaryDataFileWords] = []
    for record in candidates:
        matches: list[BinaryDataFileWords] = []
        suffix_offset = payload.find(INTEGER_HEADER_SUFFIX, 0, record.offset)
        while suffix_offset >= 2:
            header_offset = suffix_offset - 2
            element_count = int.from_bytes(
                payload[header_offset : header_offset + 2], "little"
            )
            values_offset = header_offset + 8
            values_end = values_offset + element_count * 2
            marker_offset = payload.rfind(
                BINARY_TYPE_MARKER,
                max(0, header_offset - 32),
                header_offset,
            )
            if element_count > 0 and values_end == record.offset and marker_offset >= 0:
                value_bytes = payload[values_offset:values_end]
                matches.append(
                    BinaryDataFileWords(
                        file_number=record.file_number,
                        header_offset=header_offset,
                        values_offset=values_offset,
                        element_count=element_count,
                        values_sha256=hashlib.sha256(value_bytes).hexdigest(),
                        words=tuple(
                            int.from_bytes(
                                value_bytes[offset : offset + 2],
                                "little",
                            )
                            for offset in range(0, len(value_bytes), 2)
                        ),
                    )
                )
            suffix_offset = payload.find(
                INTEGER_HEADER_SUFFIX,
                suffix_offset + 1,
                record.offset,
            )
        if len(matches) == 1:
            decoded.append(matches[0])
    return decoded


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
        integer_values=scan_integer_data_file_values(section.payload, records),
        binary_words=scan_binary_data_file_words(section.payload, records),
    )
