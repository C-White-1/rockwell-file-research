"""Resolve CCW PanelView tag addresses against an RSS data-file catalogue."""

from __future__ import annotations

import hashlib
from collections import defaultdict

from rockwell_file_research.ccw.models import CCWReport
from rockwell_file_research.integration.addresses import parse_data_table_address
from rockwell_file_research.integration.models import (
    AddressBinding,
    FileUsage,
    HMIConsumer,
    PLCHMICrossReference,
)
from rockwell_file_research.rss.models import RSSDataFileRecordEvidence, RSSInventory

SCHEMA_VERSION = "rockwell-file-research.plc-hmi-cross-reference.v1"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _consumer(
    *,
    kind: str,
    field: str,
    source_row: str,
    screen: str,
    label: str,
    include_private_text: bool,
) -> HMIConsumer:
    """Create one privacy-aware consumer evidence record."""

    return {
        "kind": kind,
        "field": field,
        "source_row": source_row,
        "screen_sha256": _sha256(screen) if screen else None,
        "label_sha256": _sha256(label),
        "screen": screen if include_private_text and screen else None,
        "label": label if include_private_text else None,
    }


def _consumers_by_tag(
    hmi: CCWReport, *, include_private_text: bool
) -> dict[str, list[HMIConsumer]]:
    """Collect exact normalized tag consumers from screen and alarm reports."""

    tag_keys = {tag["name"].casefold() for tag in hmi["tags"]}
    consumers: dict[str, list[HMIConsumer]] = defaultdict(list)
    for obj in hmi["screen_objects"]:
        for field in ("tag_1", "tag_2", "tag_3"):
            reference = obj[field].strip()
            key = reference.casefold()
            if not reference or key not in tag_keys:
                continue
            consumers[key].append(
                _consumer(
                    kind="screen_object",
                    field=field,
                    source_row=obj["source_row"],
                    screen=obj["screen"],
                    label=obj["name"],
                    include_private_text=include_private_text,
                )
            )
    for alarm in hmi["alarms"]:
        reference = alarm["trigger"].strip()
        key = reference.casefold()
        if not reference or key not in tag_keys:
            continue
        consumers[key].append(
            _consumer(
                kind="alarm",
                field="trigger",
                source_row=alarm["source_row"],
                screen="",
                label=alarm["message"],
                include_private_text=include_private_text,
            )
        )
    return consumers


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
    consumers_by_tag = _consumers_by_tag(hmi, include_private_text=include_private_text)
    bindings: list[AddressBinding] = []
    usage: dict[int, list[AddressBinding]] = defaultdict(list)
    prefixes: dict[int, set[str]] = defaultdict(set)
    counts = {"resolved": 0, "unresolved": 0, "unsupported": 0}
    numeric_candidate_exceedances = 0

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
        exceeds_candidate = (
            parsed.element_number >= record["unknown_numeric_candidate"]
            if parsed is not None
            and parsed.element_number is not None
            and record is not None
            else None
        )
        if exceeds_candidate:
            numeric_candidate_exceedances += 1
        binding: AddressBinding = {
            "status": status,
            "prefix": parsed.prefix if parsed is not None else "",
            "file_number": parsed.file_number if parsed is not None else None,
            "selector": parsed.selector if parsed is not None else None,
            "element_number": (parsed.element_number if parsed is not None else None),
            "bit_number": parsed.bit_number if parsed is not None else None,
            "member": parsed.member if parsed is not None else None,
            "exceeds_rss_numeric_candidate": exceeds_candidate,
            "tag_name_sha256": _sha256(tag["name"]),
            "address_sha256": _sha256(raw_address),
            "rss_record_name_sha256": (
                record["name_sha256"] if record is not None else None
            ),
            "tag_name": tag["name"] if include_private_text else None,
            "address": raw_address if include_private_text else None,
            "rss_record_name": record_name if include_private_text else None,
            "consumers": consumers_by_tag.get(tag["name"].casefold(), []),
        }
        bindings.append(binding)
        if parsed is not None:
            usage[parsed.file_number].append(binding)
            prefixes[parsed.file_number].add(parsed.prefix)

    file_usage: list[FileUsage] = []
    for file_number in sorted(usage):
        record = records.get(file_number)
        elements = {
            binding["element_number"]
            for binding in usage[file_number]
            if binding["element_number"] is not None
        }
        file_usage.append(
            {
                "file_number": file_number,
                "prefixes": sorted(prefixes[file_number]),
                "binding_count": len(usage[file_number]),
                "consumer_reference_count": sum(
                    len(binding["consumers"]) for binding in usage[file_number]
                ),
                "distinct_element_count": len(elements),
                "highest_element_number": max(elements) if elements else None,
                "rss_numeric_candidate": (
                    record["unknown_numeric_candidate"] if record is not None else None
                ),
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

    all_consumers = [
        consumer for consumers in consumers_by_tag.values() for consumer in consumers
    ]
    tags_with_consumers = len(consumers_by_tag)
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
            "address_elements_exceeding_rss_numeric_candidate": (
                numeric_candidate_exceedances
            ),
            "consumer_reference_count": len(all_consumers),
            "screen_object_reference_count": sum(
                consumer["kind"] == "screen_object" for consumer in all_consumers
            ),
            "alarm_reference_count": sum(
                consumer["kind"] == "alarm" for consumer in all_consumers
            ),
            "tags_with_consumers": tags_with_consumers,
            "tags_without_consumers": len(hmi["tags"]) - tags_with_consumers,
        },
        "file_usage": file_usage,
        "bindings": bindings,
        "diagnostics": [
            "Resolution proves that an HMI address names an RSS data-file number; it does not yet prove element-level ladder usage.",
            "Unsupported and unresolved addresses are retained rather than discarded or guessed.",
            "HMI element numbers exceeding the recovered RSS numeric candidate prove that field is not the data-file element extent.",
            "Consumer relationships use exact case-insensitive tag-name matches; report placeholders and column labels are not references.",
        ],
    }
