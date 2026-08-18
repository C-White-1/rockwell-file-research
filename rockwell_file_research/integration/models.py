"""Typed JSON models for cross-format PLC and HMI evidence."""

from typing import TypedDict


class CrossReferenceSource(TypedDict):
    """Integrity evidence for one input document."""

    reference: str
    size: int
    sha256: str


class AddressBinding(TypedDict):
    """One HMI tag address resolved against an RSS data-file record."""

    status: str
    prefix: str
    file_number: int | None
    tag_name_sha256: str
    address_sha256: str
    rss_record_name_sha256: str | None
    tag_name: str | None
    address: str | None
    rss_record_name: str | None


class FileUsage(TypedDict):
    """Aggregated HMI use of one RSS data file."""

    file_number: int
    prefixes: list[str]
    binding_count: int
    rss_record_name_sha256: str | None
    rss_record_name: str | None


class CrossReferenceSummary(TypedDict):
    """Resolution totals for a cross-reference document."""

    hmi_tag_count: int
    address_count: int
    resolved_count: int
    unresolved_count: int
    unsupported_count: int
    rss_catalogue_record_count: int


class PLCHMICrossReference(TypedDict):
    """Privacy-aware relationship evidence between an HMI and PLC project."""

    schema_version: str
    private_text_included: bool
    hmi_source: CrossReferenceSource
    plc_source: CrossReferenceSource
    summary: CrossReferenceSummary
    file_usage: list[FileUsage]
    bindings: list[AddressBinding]
    diagnostics: list[str]
