"""Conservative evidence extraction from RSS data-file sections."""

from __future__ import annotations

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
class DataFileSection:
    """Verified compression and redacted text evidence for one section."""

    envelope_version: int
    header_size: int
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    text_regions: list[DataFileTextRegion]


def _classify(text: str | None) -> str:
    if text in SERIALIZATION_CLASSES:
        return "serialization_class"
    if text in STANDARD_DATA_FILE_LABELS:
        return "standard_data_file_label"
    return "application_text_candidate"


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
    return DataFileSection(
        envelope_version=section.envelope_version,
        header_size=section.header_size,
        compressed_size=section.compressed_size,
        uncompressed_size=section.uncompressed_size,
        compressed_sha256=section.compressed_sha256,
        uncompressed_sha256=section.uncompressed_sha256,
        text_regions=regions,
    )
