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
    unknown_numeric_candidate: int


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


class RSSProgramTextRegion(TypedDict):
    """Classified text-region evidence in the PROGRAM FILES payload."""

    classification: str
    offset: int
    length: int
    sha256: str
    text: str | None


class RSSProgramOperandEvidence(TypedDict):
    """One candidate ladder operand with byte provenance."""

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


class RSSProgramInstructionOperandEvidence(TypedDict):
    """One ordered instruction operand with an evidence-backed role."""

    role: str
    offset: int
    length: int
    sha256: str
    value: str | None


class RSSProgramInstructionEvidence(TypedDict):
    """Instruction identity supported by a controlled binary profile."""

    mnemonic: str
    selector: int
    selector_offset: int
    operands: list[RSSProgramInstructionOperandEvidence]
    evidence_profile: str


class RSSProgramFileRecordEvidence(TypedDict):
    """One delimited ladder-file header with reference-marker evidence."""

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


class RSSProgramRungEvidence(TypedDict):
    """One corroborated rung range and privacy-safe content evidence."""

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
    application_text_candidates: list[RSSProgramTextRegion]


class RSSProgramFileEvidence(TypedDict):
    """Validated structural evidence for the PROGRAM FILES section."""

    present: bool
    envelope_version: int
    header_size: int
    compression: str
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    private_text_included: bool
    text_regions: list[RSSProgramTextRegion]
    operands: list[RSSProgramOperandEvidence]
    instructions: list[RSSProgramInstructionEvidence]
    program_file_records: list[RSSProgramFileRecordEvidence]
    rung_records: list[RSSProgramRungEvidence]
    diagnostics: list[str]


class RSSRungCommentRecordEvidence(TypedDict):
    """One MEM DATABASE comment attached to an explicit ladder rung."""

    attachment_kind: str
    attachment_key: str
    program_file_number: int | None
    rung_index: int | None
    output_address: str | None
    text_offset: int
    key_offset: int
    length: int
    sha256: str
    text: str | None
    program_rung_corroborated: bool


class RSSRungCommentEvidence(TypedDict):
    """Verified MEM DATABASE envelope and rung-comment records."""

    present: bool
    envelope_version: int
    header_size: int
    compression: str
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    private_text_included: bool
    records: list[RSSRungCommentRecordEvidence]
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
    program_files: RSSProgramFileEvidence
    rung_comments: RSSRungCommentEvidence
