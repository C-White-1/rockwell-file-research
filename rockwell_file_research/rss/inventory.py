"""Build privacy-preserving structural inventories of RSS projects."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from rockwell_file_research.rss.container import (
    CompoundDocument,
    OleCompoundDocument,
    verify_ole_signature,
)
from rockwell_file_research.rss.data_files import (
    DataFileRecord,
    inspect_data_file_section,
)
from rockwell_file_research.rss.mem_database import inspect_mem_database
from rockwell_file_research.rss.models import (
    RSSCompoundMetadata,
    RSSDataFileRecordEvidence,
    RSSDataFileSectionEvidence,
    RSSDataFileTextRegion,
    RSSInventory,
    RSSProcessorTextRegion,
    RSSProgramFileEvidence,
    RSSRungCommentEvidence,
    RSSSectionEvidence,
    RSSStreamEvidence,
)
from rockwell_file_research.rss.processor import inspect_processor_text
from rockwell_file_research.rss.program_files import inspect_program_file_section

SCHEMA_VERSION = "rss-inventory/v8"
RSS_FORMAT = "RSLogix 500 RSS OLE Compound File"

# These names are observed container-level section identifiers. Payload
# semantics remain deliberately uninterpreted in this inventory layer.
RECOGNIZED_SECTION_STREAMS = (
    "CHANNEL CONFIGURATION/ObjectData",
    "DATA FILES/ObjectData",
    "DATALOGGING CONFIGURATION/ObjectData",
    "Extensional DATA FILES/ObjectData",
    "GRAPIC FILES/ObjectData",
    "IO CONFIGURATION/ObjectData",
    "IO MISC_POWER_CONFIGURATION/ObjectData",
    "MEM DATABASE/ObjectData",
    "PROCESSOR/ObjectData",
    "PROGRAM FILES/ObjectData",
    "RCP HOLDER/ObjectData",
    "RECIPE FILES/ObjectData",
    "REVISION NOTES/ObjectData",
    "TRENDS/ObjectData",
    "Version/ObjectData",
)
DATA_FILE_SECTION_STREAMS = (
    "DATA FILES/ObjectData",
    "Extensional DATA FILES/ObjectData",
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _isoformat(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def build_inventory(
    source: Path,
    document: CompoundDocument,
    *,
    source_label: str | None = None,
    include_private_text: bool = False,
) -> RSSInventory:
    """Build an inventory from a compound document without parsing payloads."""

    source_payload = source.read_bytes()
    stream_payloads = {
        path: document.read_stream(path) for path in document.stream_paths()
    }
    streams: list[RSSStreamEvidence] = [
        {
            "path": path,
            "size": len(payload),
            "sha256": _sha256(payload),
        }
        for path, payload in sorted(stream_payloads.items())
    ]
    sections: list[RSSSectionEvidence] = []
    for path in RECOGNIZED_SECTION_STREAMS:
        payload = stream_payloads.get(path)
        sections.append(
            {
                "name": path.removesuffix("/ObjectData"),
                "stream_path": path,
                "present": payload is not None,
                "size": len(payload) if payload is not None else 0,
                "sha256": _sha256(payload) if payload is not None else "",
            }
        )
    metadata = document.metadata()
    compound_metadata: RSSCompoundMetadata = {
        "creating_application": metadata.creating_application,
        "created_at": _isoformat(metadata.created_at),
        "last_saved_at": _isoformat(metadata.last_saved_at),
    }
    recognized = set(RECOGNIZED_SECTION_STREAMS)
    processor_payload = stream_payloads.get("PROCESSOR/ObjectData")
    processor_regions: list[RSSProcessorTextRegion] = []
    if processor_payload is not None:
        processor_regions = [
            {
                "classification": region.classification,
                "offset": region.offset,
                "length": region.length,
                "sha256": region.sha256,
                "text": region.text,
            }
            for region in inspect_processor_text(
                processor_payload,
                include_private_text=include_private_text,
            )
        ]
    data_file_sections: list[RSSDataFileSectionEvidence] = []
    records_by_section: dict[str, list[DataFileRecord]] = {}
    for path in DATA_FILE_SECTION_STREAMS:
        payload = stream_payloads.get(path)
        if payload is None:
            data_file_sections.append(
                {
                    "name": path.removesuffix("/ObjectData"),
                    "present": False,
                    "envelope_version": 0,
                    "header_size": 0,
                    "compression": "",
                    "compressed_size": 0,
                    "uncompressed_size": 0,
                    "compressed_sha256": "",
                    "uncompressed_sha256": "",
                    "private_text_included": include_private_text,
                    "text_regions": [],
                    "diagnostics": [],
                }
            )
            continue
        inspected = inspect_data_file_section(
            payload,
            section_name=path.removesuffix("/ObjectData"),
            include_private_text=include_private_text,
        )
        records_by_section[path] = inspected.records
        text_regions: list[RSSDataFileTextRegion] = [
            {
                "classification": region.classification,
                "offset": region.offset,
                "length": region.length,
                "sha256": region.sha256,
                "text": region.text,
            }
            for region in inspected.text_regions
        ]
        data_file_sections.append(
            {
                "name": path.removesuffix("/ObjectData"),
                "present": True,
                "envelope_version": inspected.envelope_version,
                "header_size": inspected.header_size,
                "compression": "zlib",
                "compressed_size": inspected.compressed_size,
                "uncompressed_size": inspected.uncompressed_size,
                "compressed_sha256": inspected.compressed_sha256,
                "uncompressed_sha256": inspected.uncompressed_sha256,
                "private_text_included": include_private_text,
                "text_regions": text_regions,
                "diagnostics": [
                    (
                        "Data-file record numbers, element counts, and values remain "
                        "uninterpreted pending repeatable boundary evidence."
                    )
                ],
            }
        )
    standard_records = records_by_section.get("DATA FILES/ObjectData", [])
    extensional_records = records_by_section.get(
        "Extensional DATA FILES/ObjectData", []
    )

    def identity(record: DataFileRecord) -> tuple[int, str, str, int]:
        return (
            record.file_number,
            record.description,
            record.name,
            record.unknown_numeric_candidate,
        )

    sections_consistent = (
        bool(standard_records)
        and bool(extensional_records)
        and [identity(record) for record in standard_records]
        == [identity(record) for record in extensional_records]
    )
    extensional_by_number = {
        record.file_number: record for record in extensional_records
    }
    catalogue_records: list[RSSDataFileRecordEvidence] = []
    for record in standard_records:
        extensional = extensional_by_number.get(record.file_number)
        catalogue_records.append(
            {
                "file_number": record.file_number,
                "standard_offset": record.offset,
                "extensional_offset": extensional.offset if extensional else -1,
                "standard_marker_offset": record.marker_offset,
                "extensional_marker_offset": (
                    extensional.marker_offset if extensional else -1
                ),
                "description_sha256": record.description_sha256,
                "name_sha256": record.name_sha256,
                "description": (record.description if include_private_text else None),
                "name": record.name if include_private_text else None,
                "unknown_numeric_candidate": record.unknown_numeric_candidate,
            }
        )
    program_payload = stream_payloads.get("PROGRAM FILES/ObjectData")
    program_files: RSSProgramFileEvidence
    if program_payload is None:
        program_files = {
            "present": False,
            "envelope_version": 0,
            "header_size": 0,
            "compression": "",
            "compressed_size": 0,
            "uncompressed_size": 0,
            "compressed_sha256": "",
            "uncompressed_sha256": "",
            "private_text_included": include_private_text,
            "text_regions": [],
            "operands": [],
            "instructions": [],
            "program_file_records": [],
            "rung_records": [],
            "diagnostics": [],
        }
    else:
        inspected_program = inspect_program_file_section(
            program_payload,
            include_private_text=include_private_text,
        )
        program_files = {
            "present": True,
            "envelope_version": inspected_program.envelope_version,
            "header_size": inspected_program.header_size,
            "compression": "zlib",
            "compressed_size": inspected_program.compressed_size,
            "uncompressed_size": inspected_program.uncompressed_size,
            "compressed_sha256": inspected_program.compressed_sha256,
            "uncompressed_sha256": inspected_program.uncompressed_sha256,
            "private_text_included": include_private_text,
            "text_regions": [
                {
                    "classification": region.classification,
                    "offset": region.offset,
                    "length": region.length,
                    "sha256": region.sha256,
                    "text": region.text,
                }
                for region in inspected_program.text_regions
            ],
            "operands": [
                {
                    "offset": operand.offset,
                    "length": operand.length,
                    "sha256": operand.sha256,
                    "indirect": operand.indirect,
                    "operand": operand.operand,
                    "program_file_number": operand.program_file_number,
                    "program_file_name_sha256": operand.program_file_name_sha256,
                    "program_file_name": operand.program_file_name,
                    "rung_index": operand.rung_index,
                    "rung_start_offset": operand.rung_start_offset,
                    "rung_end_offset": operand.rung_end_offset,
                }
                for operand in inspected_program.operands
            ],
            "instructions": [
                {
                    "mnemonic": instruction.mnemonic,
                    "selector": instruction.selector,
                    "selector_offset": instruction.selector_offset,
                    "operands": [
                        {
                            "role": operand.role,
                            "offset": operand.offset,
                            "length": operand.length,
                            "sha256": operand.sha256,
                            "value": operand.value,
                        }
                        for operand in instruction.operands
                    ],
                    "evidence_profile": instruction.evidence_profile,
                }
                for instruction in inspected_program.instructions
            ],
            "program_file_records": [
                {
                    "marker_offset": record.marker_offset,
                    "end_offset": record.end_offset,
                    "file_number": record.file_number,
                    "header_numeric_candidate": record.header_numeric_candidate,
                    "name_sha256": record.name_sha256,
                    "description_sha256": record.description_sha256,
                    "name": record.name,
                    "description": record.description,
                    "rung_reference_marker_offsets": (
                        record.rung_reference_marker_offsets
                    ),
                    "declared_rung_count": record.declared_rung_count,
                    "rung_boundaries_validated": record.rung_boundaries_validated,
                    "rung_start_offsets": record.rung_start_offsets,
                }
                for record in inspected_program.program_file_records
            ],
            "rung_records": [
                {
                    "program_file_number": rung.program_file_number,
                    "program_file_name_sha256": rung.program_file_name_sha256,
                    "program_file_name": rung.program_file_name,
                    "rung_index": rung.rung_index,
                    "start_offset": rung.start_offset,
                    "end_offset": rung.end_offset,
                    "byte_length": rung.byte_length,
                    "sha256": rung.sha256,
                    "operand_count": rung.operand_count,
                    "direct_operand_count": rung.direct_operand_count,
                    "indirect_operand_count": rung.indirect_operand_count,
                    "application_text_candidate_count": (
                        rung.application_text_candidate_count
                    ),
                    "application_text_candidates": [
                        {
                            "classification": candidate.classification,
                            "offset": candidate.offset,
                            "length": candidate.length,
                            "sha256": candidate.sha256,
                            "text": candidate.text,
                        }
                        for candidate in rung.application_text_candidates
                    ],
                }
                for rung in inspected_program.rung_records
            ],
            "diagnostics": [
                (
                    "Operand candidates are length-delimited strings in the "
                    "validated ladder payload; rung boundaries are corroborated "
                    "by declared counts and class-reference markers, while "
                    "only controlled-profile simple-bit instructions are "
                    "identified; all other instruction bytes and execution "
                    "semantics remain uninterpreted."
                )
            ],
        }
    mem_payload = stream_payloads.get("MEM DATABASE/ObjectData")
    rung_comments: RSSRungCommentEvidence
    if mem_payload is None:
        rung_comments = {
            "present": False,
            "envelope_version": 0,
            "header_size": 0,
            "compression": "",
            "compressed_size": 0,
            "uncompressed_size": 0,
            "compressed_sha256": "",
            "uncompressed_sha256": "",
            "private_text_included": include_private_text,
            "records": [],
            "diagnostics": [],
        }
    else:
        inspected_mem = inspect_mem_database(
            mem_payload, include_private_text=include_private_text
        )
        validated_rungs = {
            (rung["program_file_number"], rung["rung_index"])
            for rung in program_files["rung_records"]
        }
        rung_comments = {
            "present": True,
            "envelope_version": inspected_mem.envelope_version,
            "header_size": inspected_mem.header_size,
            "compression": "zlib",
            "compressed_size": inspected_mem.compressed_size,
            "uncompressed_size": inspected_mem.uncompressed_size,
            "compressed_sha256": inspected_mem.compressed_sha256,
            "uncompressed_sha256": inspected_mem.uncompressed_sha256,
            "private_text_included": include_private_text,
            "records": [
                {
                    "attachment_kind": comment.attachment_kind,
                    "attachment_source": comment.attachment_source,
                    "attachment_key": comment.attachment_key,
                    "program_file_number": comment.program_file_number,
                    "rung_index": comment.rung_index,
                    "address": comment.address,
                    "text_offset": comment.text_offset,
                    "key_offset": comment.key_offset,
                    "length": comment.length,
                    "sha256": comment.sha256,
                    "text": comment.text,
                    "program_rung_corroborated": (
                        comment.program_file_number,
                        comment.rung_index,
                    )
                    in validated_rungs,
                }
                for comment in inspected_mem.comments
            ],
            "diagnostics": [
                (
                    "Rung comments are length-delimited MEM DATABASE text fields "
                    "followed by explicit RUNGdddddd-dddddd attachment keys."
                )
            ],
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "format": RSS_FORMAT,
        "source": {
            "reference": source_label if source_label is not None else source.name,
            "size": len(source_payload),
            "sha256": _sha256(source_payload),
        },
        "compound_metadata": compound_metadata,
        "storages": document.storage_paths(),
        "streams": streams,
        "recognized_sections": sections,
        "unrecognized_streams": sorted(set(stream_payloads) - recognized),
        "processor": {
            "present": processor_payload is not None,
            "private_text_included": include_private_text,
            "text_regions": processor_regions,
            "diagnostics": [
                (
                    "Text classifications are evidence-led candidates, not a "
                    "complete vendor specification."
                ),
                (
                    "Binary processor fields remain uninterpreted and covered by "
                    "the section SHA-256 digest."
                ),
            ],
        },
        "data_file_sections": data_file_sections,
        "data_file_catalogue": {
            "record_count": len(catalogue_records),
            "sections_consistent": sections_consistent,
            "records": catalogue_records,
            "diagnostics": [
                (
                    "Record identities and count candidates are accepted only when "
                    "the standard and extensional sections agree in order."
                ),
                (
                    "The recovered numeric field has unknown semantics; PLC–HMI "
                    "cross-reference evidence disproves data-file element count."
                ),
            ],
        },
        "program_files": program_files,
        "rung_comments": rung_comments,
    }


def inventory_rss(
    source: Path,
    *,
    source_label: str | None = None,
    include_private_text: bool = False,
) -> RSSInventory:
    """Open and structurally inventory one RSS project."""

    verify_ole_signature(source)
    with OleCompoundDocument(source) as document:
        return build_inventory(
            source,
            document,
            source_label=source_label,
            include_private_text=include_private_text,
        )
