"""Typed, JSON-compatible models for RSS structural evidence."""

from typing import TypedDict


class RSSSourceEvidence(TypedDict):
    """Privacy-preserving identity and integrity evidence for an RSS file."""

    reference: str
    size: int
    sha256: str


class RSSCompoundMetadata(TypedDict):
    """Metadata exposed by the OLE compound-file property set."""

    creating_application: str
    created_at: str
    last_saved_at: str


class RSSStreamEvidence(TypedDict):
    """Identity and integrity evidence for one OLE stream."""

    path: str
    size: int
    sha256: str


class RSSSectionEvidence(TypedDict):
    """Presence evidence for a recognized RSLogix 500 project section."""

    name: str
    stream_path: str
    present: bool
    size: int
    sha256: str


class RSSProcessorTextRegion(TypedDict):
    """Offset and integrity evidence for printable processor metadata."""

    classification: str
    offset: int
    length: int
    sha256: str
    text: str | None


class RSSProcessorEvidence(TypedDict):
    """Conservative interpretation of the RSS PROCESSOR section."""

    present: bool
    private_text_included: bool
    text_regions: list[RSSProcessorTextRegion]
    diagnostics: list[str]


class RSSDataFileTextRegion(TypedDict):
    """Offset and integrity evidence for data-file-section text."""

    classification: str
    offset: int
    length: int
    sha256: str
    text: str | None


class RSSDataFileRecordEvidence(TypedDict):
    """Cross-section evidence for one candidate data-file record."""

    file_number: int
    standard_offset: int
    extensional_offset: int
    standard_marker_offset: int
    extensional_marker_offset: int
    description_sha256: str
    name_sha256: str
    description: str | None
    name: str | None
    element_count_candidate: int


class RSSDataFileSectionEvidence(TypedDict):
    """Verified compression evidence for one RSS data-file section."""

    name: str
    present: bool
    envelope_version: int
    header_size: int
    compression: str
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    private_text_included: bool
    text_regions: list[RSSDataFileTextRegion]
    diagnostics: list[str]


class RSSDataFileCatalogueEvidence(TypedDict):
    """Record catalogue corroborated across both RSS data-file sections."""

    record_count: int
    sections_consistent: bool
    records: list[RSSDataFileRecordEvidence]
    diagnostics: list[str]


class RSSInventory(TypedDict):
    """Lossless-at-the-container-boundary inventory of an RSS project."""

    schema_version: str
    format: str
    source: RSSSourceEvidence
    compound_metadata: RSSCompoundMetadata
    storages: list[str]
    streams: list[RSSStreamEvidence]
    recognized_sections: list[RSSSectionEvidence]
    unrecognized_streams: list[str]
    processor: RSSProcessorEvidence
    data_file_sections: list[RSSDataFileSectionEvidence]
    data_file_catalogue: RSSDataFileCatalogueEvidence
