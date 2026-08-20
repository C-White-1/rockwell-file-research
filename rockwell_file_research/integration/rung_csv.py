"""Render rung-index evidence as a flat, engineer-friendly CSV."""

import csv
import io

from rockwell_file_research.integration.models import PLCHMICrossReference, RungUsage

FIELDNAMES: list[str] = [
    "evidence_type",
    "program_file_number",
    "program_file_name",
    "program_file_name_sha256",
    "rung_index",
    "rung_start_offset",
    "rung_end_offset",
    "binding_count",
    "operand_occurrence_count",
    "direct_operand_occurrence_count",
    "indirect_operand_occurrence_count",
    "consumer_reference_count",
    "tag_names",
    "tag_name_sha256s",
    "application_text_candidate_count",
    "application_text_candidates",
    "application_text_candidate_sha256s",
]


def _row(
    evidence_type: str,
    usage: RungUsage,
    *,
    omit_hashes: bool,
) -> dict[str, object]:
    """Flatten one rung-usage record without changing evidence strength."""

    return {
        "evidence_type": evidence_type,
        "program_file_number": usage["program_file_number"],
        "program_file_name": usage["program_file_name"] or "",
        "program_file_name_sha256": (
            "" if omit_hashes else usage["program_file_name_sha256"]
        ),
        "rung_index": usage["rung_index"],
        "rung_start_offset": usage["rung_start_offset"],
        "rung_end_offset": usage["rung_end_offset"],
        "binding_count": usage["binding_count"],
        "operand_occurrence_count": usage["operand_occurrence_count"],
        "direct_operand_occurrence_count": usage["direct_operand_occurrence_count"],
        "indirect_operand_occurrence_count": usage["indirect_operand_occurrence_count"],
        "consumer_reference_count": usage["consumer_reference_count"],
        "tag_names": "; ".join(usage["tag_names"]),
        "tag_name_sha256s": (
            "" if omit_hashes else "; ".join(usage["tag_name_sha256s"])
        ),
        "application_text_candidate_count": len(usage["application_text_candidates"]),
        "application_text_candidates": "; ".join(
            candidate["text"] or ""
            for candidate in usage["application_text_candidates"]
        ),
        "application_text_candidate_sha256s": (
            ""
            if omit_hashes
            else "; ".join(
                candidate["sha256"]
                for candidate in usage["application_text_candidates"]
            )
        ),
    }


def render_rung_usage_csv(
    report: PLCHMICrossReference,
    *,
    omit_hashes: bool = False,
) -> str:
    """Render exact and contained-bit rung evidence with explicit types."""

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for usage in report["rung_usage"]:
        writer.writerow(_row("exact", usage, omit_hashes=omit_hashes))
    for usage in report["contained_bit_rung_usage"]:
        writer.writerow(_row("contained_bit", usage, omit_hashes=omit_hashes))
    return stream.getvalue()
