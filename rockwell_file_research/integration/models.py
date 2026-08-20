"""Typed JSON models for cross-format PLC and HMI evidence."""

from typing import TypedDict


class CrossReferenceSource(TypedDict):
    """Integrity evidence for one input document."""

    reference: str
    size: int
    sha256: str


class HMIConsumer(TypedDict):
    """One exact HMI screen-object or alarm reference to a tag."""

    kind: str
    field: str
    source_row: str
    screen_sha256: str | None
    label_sha256: str
    screen: str | None
    label: str | None


class LadderOperandOccurrence(TypedDict):
    """One matching operand occurrence in the RSS PROGRAM FILES payload."""

    offset: int
    indirect: bool
    operand_sha256: str
    operand: str | None
    program_file_number: int | None
    program_file_name_sha256: str | None
    program_file_name: str | None
    rung_index: int | None
    rung_start_offset: int | None
    rung_end_offset: int | None


class AddressBinding(TypedDict):
    """One HMI tag address resolved against an RSS data-file record."""

    status: str
    prefix: str
    file_number: int | None
    selector: str | None
    element_number: int | None
    subelement_number: int | None
    bit_number: int | None
    member: str | None
    exceeds_rss_numeric_candidate: bool | None
    tag_name_sha256: str
    address_sha256: str
    rss_record_name_sha256: str | None
    tag_name: str | None
    address: str | None
    rss_record_name: str | None
    consumers: list[HMIConsumer]
    ladder_occurrences: list[LadderOperandOccurrence]
    contained_bit_occurrences: list[LadderOperandOccurrence]


class FileUsage(TypedDict):
    """Aggregated HMI use of one RSS data file."""

    file_number: int
    prefixes: list[str]
    binding_count: int
    consumer_reference_count: int
    ladder_operand_occurrence_count: int
    distinct_ladder_rung_count: int
    contained_bit_occurrence_count: int
    distinct_element_count: int
    highest_element_number: int | None
    rss_numeric_candidate: int | None
    rss_record_name_sha256: str | None
    rss_record_name: str | None


class RungUsage(TypedDict):
    """Exact HMI binding evidence grouped by one corroborated ladder rung."""

    program_file_number: int
    program_file_name_sha256: str
    program_file_name: str | None
    rung_index: int
    rung_start_offset: int | None
    rung_end_offset: int | None
    binding_count: int
    operand_occurrence_count: int
    direct_operand_occurrence_count: int
    indirect_operand_occurrence_count: int
    consumer_reference_count: int
    tag_name_sha256s: list[str]
    tag_names: list[str]


class CrossReferenceSummary(TypedDict):
    """Resolution totals for a cross-reference document."""

    hmi_tag_count: int
    address_count: int
    resolved_count: int
    unresolved_count: int
    unsupported_count: int
    rss_catalogue_record_count: int
    address_elements_exceeding_rss_numeric_candidate: int
    consumer_reference_count: int
    screen_object_reference_count: int
    alarm_reference_count: int
    tags_with_consumers: int
    tags_without_consumers: int
    ladder_operand_occurrence_count: int
    ladder_program_file_count: int
    distinct_ladder_rung_count: int
    rung_scoped_ladder_operand_occurrence_count: int
    direct_ladder_operand_occurrence_count: int
    indirect_ladder_operand_occurrence_count: int
    bindings_with_ladder_evidence: int
    bindings_without_ladder_evidence: int
    contained_bit_occurrence_count: int
    bindings_with_contained_bit_evidence: int
    contained_bit_program_file_count: int
    distinct_contained_bit_rung_count: int
    rung_scoped_contained_bit_occurrence_count: int


class PLCHMICrossReference(TypedDict):
    """Privacy-aware relationship evidence between an HMI and PLC project."""

    schema_version: str
    private_text_included: bool
    hmi_source: CrossReferenceSource
    plc_source: CrossReferenceSource
    summary: CrossReferenceSummary
    file_usage: list[FileUsage]
    rung_usage: list[RungUsage]
    contained_bit_rung_usage: list[RungUsage]
    bindings: list[AddressBinding]
    diagnostics: list[str]
