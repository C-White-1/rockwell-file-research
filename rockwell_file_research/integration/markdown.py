"""Render PLC–HMI cross-reference evidence as readable Markdown."""

from rockwell_file_research.integration.models import (
    AddressBinding,
    HMIConsumer,
    PLCHMICrossReference,
)


def _cell(value: object) -> str:
    """Escape one compact Markdown table cell."""

    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _consumer_text(consumer: HMIConsumer) -> str:
    label = consumer["label"] or consumer["label_sha256"]
    if consumer["kind"] == "screen_object":
        screen = consumer["screen"] or consumer["screen_sha256"]
        return f"screen {screen}: {label}"
    return f"alarm: {label}"


def _location(binding: AddressBinding) -> str:
    parts: list[str] = []
    if binding["element_number"] is not None:
        parts.append(f"element {binding['element_number']}")
    if binding["subelement_number"] is not None:
        parts.append(f"subelement {binding['subelement_number']}")
    if binding["bit_number"] is not None:
        parts.append(f"bit {binding['bit_number']}")
    if binding["member"] is not None:
        parts.append(f"member {binding['member']}")
    return ", ".join(parts) or "-"


def render_cross_reference_markdown(report: PLCHMICrossReference) -> str:
    """Render a deterministic summary and complete binding table."""

    summary = report["summary"]
    lines = [
        "<!-- markdownlint-disable MD013 -->",
        "",
        "# PLC–HMI Cross-reference",
        "",
        "## Summary",
        "",
        f"- HMI tags: {summary['hmi_tag_count']}",
        f"- Resolved addresses: {summary['resolved_count']} of {summary['address_count']}",
        f"- Screen-object references: {summary['screen_object_reference_count']}",
        f"- Alarm references: {summary['alarm_reference_count']}",
        f"- Tags with consumers: {summary['tags_with_consumers']}",
        f"- Tags without consumers: {summary['tags_without_consumers']}",
        f"- Bindings with ladder evidence: {summary['bindings_with_ladder_evidence']}",
        f"- Bindings without ladder evidence: {summary['bindings_without_ladder_evidence']}",
        f"- Matching ladder operand occurrences: {summary['ladder_operand_occurrence_count']}",
        f"- Contained-bit ladder occurrences: {summary['contained_bit_occurrence_count']}",
        "",
        "## RSS data-file usage",
        "",
        "| File | Prefixes | Bindings | Consumers | Exact ladder | Contained bits | Distinct elements | Highest element | RSS record |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for usage in report["file_usage"]:
        record_name = usage["rss_record_name"] or usage["rss_record_name_sha256"]
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    usage["file_number"],
                    ", ".join(usage["prefixes"]),
                    usage["binding_count"],
                    usage["consumer_reference_count"],
                    usage["ladder_operand_occurrence_count"],
                    usage["contained_bit_occurrence_count"],
                    usage["distinct_element_count"],
                    usage["highest_element_number"],
                    record_name,
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Complete bindings",
            "",
            "| Tag | PLC address | File | Location | RSS record | Exact ladder | Contained bits | Consumers |",
            "| --- | --- | ---: | --- | --- | ---: | ---: | --- |",
        ]
    )
    for binding in report["bindings"]:
        tag = binding["tag_name"] or binding["tag_name_sha256"]
        address = binding["address"] or binding["address_sha256"]
        record_name = (
            binding["rss_record_name"] or binding["rss_record_name_sha256"] or "-"
        )
        consumers = "; ".join(
            _consumer_text(consumer) for consumer in binding["consumers"]
        )
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    tag,
                    address,
                    binding["file_number"],
                    _location(binding),
                    record_name,
                    len(binding["ladder_occurrences"]),
                    len(binding["contained_bit_occurrences"]),
                    consumers,
                )
            )
            + " |"
        )
    lines.extend(["", "## Evidence limitations", ""])
    lines.extend(f"- {diagnostic}" for diagnostic in report["diagnostics"])
    return "\n".join(lines) + "\n"
