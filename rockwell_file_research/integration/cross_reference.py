"""Resolve CCW PanelView tag addresses against an RSS data-file catalogue."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Literal

from rockwell_file_research.ccw.models import CCWReport
from rockwell_file_research.integration.addresses import (
    canonical_address_key,
    parse_data_table_address,
)
from rockwell_file_research.integration.models import (
    AddressBinding,
    FileUsage,
    HMIConsumer,
    LadderOperandOccurrence,
    PLCHMICrossReference,
    RungTextCandidate,
    RungUsage,
)
from rockwell_file_research.rss.models import (
    RSSDataFileRecordEvidence,
    RSSInventory,
    RSSProgramRungEvidence,
)

SCHEMA_VERSION = "rockwell-file-research.plc-hmi-cross-reference.v6"


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


def _ladder_occurrence_indexes(
    plc: RSSInventory, *, include_private_text: bool
) -> tuple[
    dict[
        tuple[str, int, int | None, int | None, int | None, str | None],
        list[LadderOperandOccurrence],
    ],
    dict[
        tuple[str, int, int | None, int | None, int | None, str | None],
        list[LadderOperandOccurrence],
    ],
]:
    """Index exact operands and contained bit operands by normalized address."""

    occurrences: dict[
        tuple[str, int, int | None, int | None, int | None, str | None],
        list[LadderOperandOccurrence],
    ] = defaultdict(list)
    contained_bits: dict[
        tuple[str, int, int | None, int | None, int | None, str | None],
        list[LadderOperandOccurrence],
    ] = defaultdict(list)
    for operand in plc["program_files"]["operands"]:
        raw = operand["operand"]
        if raw is None:
            continue
        parsed = parse_data_table_address(raw.removeprefix("#"))
        if parsed is None:
            continue
        occurrence: LadderOperandOccurrence = {
            "offset": operand["offset"],
            "indirect": operand["indirect"],
            "operand_sha256": operand["sha256"],
            "operand": raw if include_private_text else None,
            "program_file_number": operand["program_file_number"],
            "program_file_name_sha256": operand["program_file_name_sha256"],
            "program_file_name": (
                operand["program_file_name"] if include_private_text else None
            ),
            "rung_index": operand["rung_index"],
            "rung_start_offset": operand["rung_start_offset"],
            "rung_end_offset": operand["rung_end_offset"],
        }
        key = canonical_address_key(parsed)
        occurrences[key].append(occurrence)
        if parsed.bit_number is not None:
            word_key = (key[0], key[1], key[2], key[3], None, None)
            contained_bits[word_key].append(occurrence)
    return occurrences, contained_bits


def _rung_usage(
    bindings: list[AddressBinding],
    occurrence_field: Literal["ladder_occurrences", "contained_bit_occurrences"],
    rung_records: dict[tuple[int, int], RSSProgramRungEvidence],
    *,
    include_private_text: bool,
) -> list[RungUsage]:
    """Group one address-evidence class by corroborated file and rung."""

    grouped: dict[
        tuple[int, int], list[tuple[AddressBinding, LadderOperandOccurrence]]
    ] = defaultdict(list)
    for binding in bindings:
        for occurrence in binding[occurrence_field]:
            file_number = occurrence["program_file_number"]
            rung_index = occurrence["rung_index"]
            if file_number is None or rung_index is None:
                continue
            grouped[(file_number, rung_index)].append((binding, occurrence))

    result: list[RungUsage] = []
    for (file_number, rung_index), matches in sorted(grouped.items()):
        first_occurrence = matches[0][1]
        rung_record = rung_records.get((file_number, rung_index))
        unique_bindings = {
            (binding["tag_name_sha256"], binding["address_sha256"]): binding
            for binding, _occurrence in matches
        }
        text_candidates: list[RungTextCandidate] = []
        if rung_record is not None:
            text_candidates = [
                {
                    "offset": candidate["offset"],
                    "length": candidate["length"],
                    "sha256": candidate["sha256"],
                    "text": (candidate["text"] if include_private_text else None),
                }
                for candidate in rung_record["application_text_candidates"]
            ]
        result.append(
            {
                "program_file_number": file_number,
                "program_file_name_sha256": (
                    first_occurrence["program_file_name_sha256"] or ""
                ),
                "program_file_name": first_occurrence["program_file_name"],
                "rung_index": rung_index,
                "rung_start_offset": first_occurrence["rung_start_offset"],
                "rung_end_offset": first_occurrence["rung_end_offset"],
                "rung_byte_length": (
                    rung_record.get("byte_length") if rung_record is not None else None
                ),
                "rung_sha256": (
                    rung_record.get("sha256") if rung_record is not None else None
                ),
                "rung_operand_count": (
                    rung_record.get("operand_count")
                    if rung_record is not None
                    else None
                ),
                "rung_direct_operand_count": (
                    rung_record.get("direct_operand_count")
                    if rung_record is not None
                    else None
                ),
                "rung_indirect_operand_count": (
                    rung_record.get("indirect_operand_count")
                    if rung_record is not None
                    else None
                ),
                "binding_count": len(unique_bindings),
                "operand_occurrence_count": len(matches),
                "distinct_matched_operand_count": len(
                    {occurrence["offset"] for _binding, occurrence in matches}
                ),
                "direct_operand_occurrence_count": sum(
                    not occurrence["indirect"] for _binding, occurrence in matches
                ),
                "indirect_operand_occurrence_count": sum(
                    occurrence["indirect"] for _binding, occurrence in matches
                ),
                "consumer_reference_count": sum(
                    len(binding["consumers"]) for binding in unique_bindings.values()
                ),
                "tag_name_sha256s": sorted(
                    binding["tag_name_sha256"] for binding in unique_bindings.values()
                ),
                "tag_names": sorted(
                    binding["tag_name"]
                    for binding in unique_bindings.values()
                    if binding["tag_name"] is not None
                ),
                "application_text_candidates": text_candidates,
            }
        )
    return result


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
    rung_records = {
        (record["program_file_number"], record["rung_index"]): record
        for record in plc["program_files"].get("rung_records", [])
    }
    consumers_by_tag = _consumers_by_tag(hmi, include_private_text=include_private_text)
    ladder_occurrences_by_address, contained_bits_by_address = (
        _ladder_occurrence_indexes(plc, include_private_text=include_private_text)
    )
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
        ladder_occurrences = (
            ladder_occurrences_by_address.get(canonical_address_key(parsed), [])
            if parsed is not None
            else []
        )
        contained_bit_occurrences = (
            contained_bits_by_address.get(canonical_address_key(parsed), [])
            if parsed is not None
            and parsed.bit_number is None
            and parsed.member is None
            else []
        )
        binding: AddressBinding = {
            "status": status,
            "prefix": parsed.prefix if parsed is not None else "",
            "file_number": parsed.file_number if parsed is not None else None,
            "selector": parsed.selector if parsed is not None else None,
            "element_number": (parsed.element_number if parsed is not None else None),
            "subelement_number": (
                parsed.subelement_number if parsed is not None else None
            ),
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
            "ladder_occurrences": ladder_occurrences,
            "contained_bit_occurrences": contained_bit_occurrences,
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
                "ladder_operand_occurrence_count": sum(
                    len(binding["ladder_occurrences"]) for binding in usage[file_number]
                ),
                "distinct_ladder_rung_count": len(
                    {
                        (
                            occurrence["program_file_number"],
                            occurrence["rung_index"],
                        )
                        for binding in usage[file_number]
                        for occurrence in binding["ladder_occurrences"]
                        if occurrence["program_file_number"] is not None
                        and occurrence["rung_index"] is not None
                    }
                ),
                "contained_bit_occurrence_count": sum(
                    len(binding["contained_bit_occurrences"])
                    for binding in usage[file_number]
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
    all_ladder_occurrences = [
        occurrence
        for binding in bindings
        for occurrence in binding["ladder_occurrences"]
    ]
    bindings_with_ladder_evidence = sum(
        bool(binding["ladder_occurrences"]) for binding in bindings
    )
    scoped_ladder_occurrences = [
        occurrence
        for occurrence in all_ladder_occurrences
        if occurrence["program_file_number"] is not None
        and occurrence["rung_index"] is not None
    ]
    all_contained_bit_occurrences = [
        occurrence
        for binding in bindings
        for occurrence in binding["contained_bit_occurrences"]
    ]
    bindings_with_contained_bit_evidence = sum(
        bool(binding["contained_bit_occurrences"]) for binding in bindings
    )
    scoped_contained_bit_occurrences = [
        occurrence
        for occurrence in all_contained_bit_occurrences
        if occurrence["program_file_number"] is not None
        and occurrence["rung_index"] is not None
    ]
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
            "ladder_operand_occurrence_count": len(all_ladder_occurrences),
            "distinct_ladder_operand_count": len(
                {
                    (occurrence["program_file_number"], occurrence["offset"])
                    for occurrence in all_ladder_occurrences
                }
            ),
            "ladder_program_file_count": len(
                {
                    occurrence["program_file_number"]
                    for occurrence in scoped_ladder_occurrences
                }
            ),
            "distinct_ladder_rung_count": len(
                {
                    (
                        occurrence["program_file_number"],
                        occurrence["rung_index"],
                    )
                    for occurrence in scoped_ladder_occurrences
                }
            ),
            "rung_scoped_ladder_operand_occurrence_count": len(
                scoped_ladder_occurrences
            ),
            "direct_ladder_operand_occurrence_count": sum(
                not occurrence["indirect"] for occurrence in all_ladder_occurrences
            ),
            "indirect_ladder_operand_occurrence_count": sum(
                occurrence["indirect"] for occurrence in all_ladder_occurrences
            ),
            "bindings_with_ladder_evidence": bindings_with_ladder_evidence,
            "bindings_without_ladder_evidence": (
                len(bindings) - bindings_with_ladder_evidence
            ),
            "contained_bit_occurrence_count": len(all_contained_bit_occurrences),
            "distinct_contained_bit_operand_count": len(
                {
                    (occurrence["program_file_number"], occurrence["offset"])
                    for occurrence in all_contained_bit_occurrences
                }
            ),
            "bindings_with_contained_bit_evidence": (
                bindings_with_contained_bit_evidence
            ),
            "contained_bit_program_file_count": len(
                {
                    occurrence["program_file_number"]
                    for occurrence in scoped_contained_bit_occurrences
                }
            ),
            "distinct_contained_bit_rung_count": len(
                {
                    (
                        occurrence["program_file_number"],
                        occurrence["rung_index"],
                    )
                    for occurrence in scoped_contained_bit_occurrences
                }
            ),
            "rung_scoped_contained_bit_occurrence_count": len(
                scoped_contained_bit_occurrences
            ),
        },
        "file_usage": file_usage,
        "rung_usage": _rung_usage(
            bindings,
            "ladder_occurrences",
            rung_records,
            include_private_text=include_private_text,
        ),
        "contained_bit_rung_usage": _rung_usage(
            bindings,
            "contained_bit_occurrences",
            rung_records,
            include_private_text=include_private_text,
        ),
        "bindings": bindings,
        "diagnostics": [
            "Ladder occurrence matches prove that equivalent operand strings occur in a corroborated program-file and rung byte range; instruction type and execution semantics remain uninterpreted.",
            "Contained-bit evidence links a whole-word HMI address to ladder bit operands within that word; it is reported separately from exact operand matches.",
            "Unsupported and unresolved addresses are retained rather than discarded or guessed.",
            "HMI element numbers exceeding the recovered RSS numeric candidate prove that field is not the data-file element extent.",
            "Consumer relationships use exact case-insensitive tag-name matches; report placeholders and column labels are not references.",
        ],
    }
