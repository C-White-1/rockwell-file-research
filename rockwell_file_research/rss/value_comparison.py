"""Compare corroborated RSS data-file arrays without weakening redaction."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from rockwell_file_research.rss.binary_values import corroborate_binary_data_file
from rockwell_file_research.rss.integer_values import corroborate_integer_data_file
from rockwell_file_research.rss.models import RSSInventory
from rockwell_file_research.rss.value_semantics import SemanticValueProfile

FIELDNAMES = [
    "data_type",
    "file_number",
    "element_index",
    "address",
    "status",
    "semantic_status",
    "semantic_name",
    "left_interpretation",
    "right_interpretation",
    "semantic_evidence",
    "left_decimal_value",
    "right_decimal_value",
    "left_hex_value",
    "right_hex_value",
    "left_array_sha256",
    "right_array_sha256",
    "diagnostic",
]


@dataclass(frozen=True)
class DataValueComparison:
    """One address-level comparison backed by corroborated array evidence."""

    data_type: str
    file_number: int
    element_index: int
    address: str
    status: str
    left_value: int | None
    right_value: int | None
    left_sha256: str | None
    right_sha256: str | None
    diagnostic: str


def _file_numbers(inventory: RSSInventory, key: str) -> set[int]:
    """Collect file numbers without treating either redundant section as primary."""

    return {
        array["file_number"]
        for section in inventory["data_file_sections"]
        for array in section[key]  # type: ignore[literal-required]
    }


def _compare_array(
    *,
    data_type: str,
    file_number: int,
    prefix: str,
    left_count: int | None,
    right_count: int | None,
    left_sha256: str | None,
    right_sha256: str | None,
    left_values: tuple[int, ...] | None,
    right_values: tuple[int, ...] | None,
    left_exists: bool,
    right_exists: bool,
    left_consistent: bool,
    right_consistent: bool,
) -> list[DataValueComparison]:
    count = max(left_count or 0, right_count or 0, 1)
    rows: list[DataValueComparison] = []
    for index in range(count):
        address = f"{prefix}{file_number}:{index}"
        left_present = left_count is not None and index < left_count
        right_present = right_count is not None and index < right_count
        left_value = (
            left_values[index] if left_values is not None and left_present else None
        )
        right_value = (
            right_values[index] if right_values is not None and right_present else None
        )

        if not left_exists:
            status = "missing_left"
            diagnostic = "Data file is absent from the left inventory."
        elif not right_exists:
            status = "missing_right"
            diagnostic = "Data file is absent from the right inventory."
        elif not left_consistent or not right_consistent:
            status = "unresolved"
            diagnostic = "One or both inventories lack corroborated array evidence."
        elif not left_present:
            status = "missing_left"
            diagnostic = "Address is absent from the left array."
        elif not right_present:
            status = "missing_right"
            diagnostic = "Address is absent from the right array."
        elif left_values is not None and right_values is not None:
            status = "equal" if left_value == right_value else "changed"
            diagnostic = (
                "Decoded values are equal."
                if status == "equal"
                else "Decoded values differ."
            )
        elif left_sha256 == right_sha256:
            status = "equal_by_array_digest"
            diagnostic = "Redacted arrays have equal SHA-256 evidence."
        else:
            status = "redacted_difference"
            diagnostic = (
                "Array digests differ; address-level change is not knowable "
                "without private values."
            )

        rows.append(
            DataValueComparison(
                data_type,
                file_number,
                index,
                address,
                status,
                left_value,
                right_value,
                left_sha256,
                right_sha256,
                diagnostic,
            )
        )
    return rows


def compare_data_values(
    left: RSSInventory, right: RSSInventory
) -> tuple[DataValueComparison, ...]:
    """Compare every decoded integer and binary array in two inventories."""

    rows: list[DataValueComparison] = []
    integer_files = _file_numbers(left, "integer_value_arrays") | _file_numbers(
        right, "integer_value_arrays"
    )
    for file_number in sorted(integer_files):
        lhs = corroborate_integer_data_file(left["data_file_sections"], file_number)
        rhs = corroborate_integer_data_file(right["data_file_sections"], file_number)
        rows.extend(
            _compare_array(
                data_type="integer",
                file_number=file_number,
                prefix="N",
                left_count=lhs.element_count,
                right_count=rhs.element_count,
                left_sha256=lhs.values_sha256,
                right_sha256=rhs.values_sha256,
                left_values=lhs.values,
                right_values=rhs.values,
                left_exists=file_number in _file_numbers(left, "integer_value_arrays"),
                right_exists=file_number
                in _file_numbers(right, "integer_value_arrays"),
                left_consistent=lhs.sections_consistent,
                right_consistent=rhs.sections_consistent,
            )
        )

    binary_files = _file_numbers(left, "binary_word_arrays") | _file_numbers(
        right, "binary_word_arrays"
    )
    for file_number in sorted(binary_files):
        lhs = corroborate_binary_data_file(left["data_file_sections"], file_number)
        rhs = corroborate_binary_data_file(right["data_file_sections"], file_number)
        rows.extend(
            _compare_array(
                data_type="binary_word",
                file_number=file_number,
                prefix="B",
                left_count=lhs.element_count,
                right_count=rhs.element_count,
                left_sha256=lhs.values_sha256,
                right_sha256=rhs.values_sha256,
                left_values=lhs.words,
                right_values=rhs.words,
                left_exists=file_number in _file_numbers(left, "binary_word_arrays"),
                right_exists=file_number in _file_numbers(right, "binary_word_arrays"),
                left_consistent=lhs.sections_consistent,
                right_consistent=rhs.sections_consistent,
            )
        )
    return tuple(rows)


def render_data_value_comparison_csv(
    comparisons: tuple[DataValueComparison, ...],
    *,
    left_profile: SemanticValueProfile | None = None,
    right_profile: SemanticValueProfile | None = None,
    semantic_only: bool = False,
) -> str:
    """Render deterministic comparison rows suitable for private or redacted use."""

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for item in comparisons:
        left_rule = (
            None
            if left_profile is None or item.left_value is None
            else left_profile.get((item.address.upper(), item.left_value))
        )
        right_rule = (
            None
            if right_profile is None or item.right_value is None
            else right_profile.get((item.address.upper(), item.right_value))
        )
        names = {
            rule.semantic_name for rule in (left_rule, right_rule) if rule is not None
        }
        evidence = {
            rule.evidence for rule in (left_rule, right_rule) if rule is not None
        }
        if left_rule is None and right_rule is None:
            semantic_status = "unprofiled"
        elif left_rule is None or right_rule is None:
            semantic_status = "partially_mapped"
        elif (
            left_rule.semantic_name == right_rule.semantic_name
            and left_rule.interpretation == right_rule.interpretation
        ):
            semantic_status = "semantic_equal"
        else:
            semantic_status = "semantic_changed"
        if semantic_only and semantic_status == "unprofiled":
            continue
        writer.writerow(
            {
                "data_type": item.data_type,
                "file_number": item.file_number,
                "element_index": item.element_index,
                "address": item.address,
                "status": item.status,
                "semantic_status": semantic_status,
                "semantic_name": "; ".join(sorted(names)),
                "left_interpretation": (
                    "" if left_rule is None else left_rule.interpretation
                ),
                "right_interpretation": (
                    "" if right_rule is None else right_rule.interpretation
                ),
                "semantic_evidence": "; ".join(sorted(evidence)),
                "left_decimal_value": ""
                if item.left_value is None
                else item.left_value,
                "right_decimal_value": (
                    "" if item.right_value is None else item.right_value
                ),
                "left_hex_value": (
                    "" if item.left_value is None else f"{item.left_value & 0xFFFF:04X}"
                ),
                "right_hex_value": (
                    ""
                    if item.right_value is None
                    else f"{item.right_value & 0xFFFF:04X}"
                ),
                "left_array_sha256": item.left_sha256 or "",
                "right_array_sha256": item.right_sha256 or "",
                "diagnostic": item.diagnostic,
            }
        )
    return stream.getvalue()


def _markdown_cell(value: str) -> str:
    """Escape one generated Markdown table cell."""

    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_data_value_comparison_markdown(
    comparisons: tuple[DataValueComparison, ...],
    *,
    left_profile: SemanticValueProfile | None = None,
    right_profile: SemanticValueProfile | None = None,
    semantic_only: bool = False,
) -> str:
    """Render the same comparison evidence as a concise engineering report."""

    csv_text = render_data_value_comparison_csv(
        comparisons,
        left_profile=left_profile,
        right_profile=right_profile,
        semantic_only=semantic_only,
    )
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    semantic_changes = sum(row["semantic_status"] == "semantic_changed" for row in rows)
    raw_changes = sum(row["status"] == "changed" for row in rows)
    unresolved = sum(
        row["status"] in {"unresolved", "redacted_difference"} for row in rows
    )
    lines = [
        "# RSS Data-Value Comparison",
        "",
        "> Scope: saved project values only; this is not a live controller observation.",
        "",
        "## Summary",
        "",
        "| Measure | Count |",
        "| --- | ---: |",
        f"| Reported addresses | {len(rows)} |",
        f"| Raw value changes | {raw_changes} |",
        f"| Semantic changes | {semantic_changes} |",
        f"| Unresolved or redacted differences | {unresolved} |",
        "",
        "## Settings",
        "",
        "<!-- markdownlint-disable MD013 -->",
        "| Address | Setting | Raw status | Semantic status | Left value | Left meaning | Right value | Right meaning |",
        "| --- | --- | --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in rows:
        cells = [
            row["address"],
            row["semantic_name"].replace("_", " ").title(),
            row["status"],
            row["semantic_status"],
            row["left_decimal_value"],
            row["left_interpretation"],
            row["right_decimal_value"],
            row["right_interpretation"],
        ]
        lines.append("| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |")
    lines.extend(
        [
            "<!-- markdownlint-enable MD013 -->",
            "",
            "## Evidence boundary",
            "",
            "Semantic names and interpretations come only from supplied evidence",
            "profiles. Unprofiled values remain unnamed. Raw equality and semantic",
            "equality are reported separately because variant-specific profiles may",
            "assign different meanings to the same numeric value.",
            "",
        ]
    )
    return "\n".join(lines)
