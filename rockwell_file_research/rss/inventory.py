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
from rockwell_file_research.rss.data_files import inspect_data_file_section
from rockwell_file_research.rss.models import (
    RSSCompoundMetadata,
    RSSDataFileSectionEvidence,
    RSSDataFileTextRegion,
    RSSInventory,
    RSSProcessorTextRegion,
    RSSSectionEvidence,
    RSSStreamEvidence,
)
from rockwell_file_research.rss.processor import inspect_processor_text

SCHEMA_VERSION = "rss-inventory/v1"
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
