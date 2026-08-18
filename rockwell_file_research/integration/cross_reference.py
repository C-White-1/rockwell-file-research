"""Resolve CCW PanelView tag addresses against an RSS data-file catalogue."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from rockwell_file_research.ccw.models import CCWReport
from rockwell_file_research.integration.addresses import parse_data_table_address
from rockwell_file_research.integration.models import (
    AddressBinding,
    FileUsage,
    PLCHMICrossReference,
)
from rockwell_file_research.rss.models import RSSDataFileRecordEvidence, RSSInventory

SCHEMA_VERSION = "rockwell-file-research.plc-hmi-cross-reference.v1"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_plc_hmi_cross_reference(
    hmi: CCWReport,
    plc: RSSInventory,
    *,
    include_private_text: bool = False,
) -> PLCHMICrossReference:
    """Join HMI tag addresses to RSS files while preserving uncertainty."""

    records = {
        record["file_number"]: record
        for record in plc["data_file_catalogue"]["records"]
    }
    bindings: list[AddressBinding] = []
    usage: dict[int, list[AddressBinding]] = defaultdict(list)
    prefixes: dict[int, set[str]] = defaultdict(set)
    counts = {"resolved": 0, "unresolved": 0, "unsupported": 0}

    for tag in hmi["tags"]:
        raw_address = tag["address"].strip()
        parsed = parse_data_table_address(raw_address)
        record: RSSDataFileRecordEvidence | None = None
        if parsed is None:
            status = "unsupported"
            counts[status] += 1
        else:
            record = records.get(parsed.file_number)
            status = "resolved" if record is not None else "unresolved"
            counts[status] += 1
        record_name = record["name"] if record is not None else None
        binding: AddressBinding = {
            "status": status,
            "prefix": parsed.prefix if parsed is not None else "",
            "file_number": parsed.file_number if parsed is not None else None,
            "tag_name_sha256": _sha256(tag["name"]),
            "address_sha256": _sha256(raw_address),
            "rss_record_name_sha256": (
                record["name_sha256"] if record is not None else None
            ),
            "tag_name": tag["name"] if include_private_text else None,
            "address": raw_address if include_private_text else None,
            "rss_record_name": record_name if include_private_text else None,
        }
        bindings.append(binding)
        if parsed is not None:
            usage[parsed.file_number].append(binding)
            prefixes[parsed.file_number].add(parsed.prefix)

    file_usage: list[FileUsage] = []
    for file_number in sorted(usage):
        record = records.get(file_number)
        file_usage.append(
            {
                "file_number": file_number,
                "prefixes": sorted(prefixes[file_number]),
                "binding_count": len(usage[file_number]),
                "rss_record_name_sha256": (
                    record["name_sha256"] if record is not None else None
                ),
                "rss_record_name": (
                    record["name"]
                    if include_private_text and record is not None
                    else None
                ),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "private_text_included": include_private_text,
        "hmi_source": {
            "reference": hmi["source"]["path"],
            "size": hmi["source"]["size"],
            "sha256": hmi["source"]["sha256"],
        },
        "plc_source": plc["source"],
        "summary": {
            "hmi_tag_count": len(hmi["tags"]),
            "address_count": sum(bool(tag["address"].strip()) for tag in hmi["tags"]),
            "resolved_count": counts["resolved"],
            "unresolved_count": counts["unresolved"],
            "unsupported_count": counts["unsupported"],
            "rss_catalogue_record_count": plc["data_file_catalogue"]["record_count"],
        },
        "file_usage": file_usage,
        "bindings": bindings,
        "diagnostics": [
            "Resolution proves that an HMI address names an RSS data-file number; it does not yet prove element-level ladder usage.",
            "Unsupported and unresolved addresses are retained rather than discarded or guessed.",
        ],
    }
