"""Rung-level coverage for probable RSS instruction candidates."""

import csv
import io
from collections import defaultdict

from rockwell_file_research.rss.models import (
    RSSInventory,
    RSSProgramInstructionCandidateEvidence,
)

FIELDNAMES = (
    "program_file_number",
    "program_file_name",
    "program_file_name_sha256",
    "rung_index",
    "recovered_operand_count",
    "candidate_instruction_count",
    "candidate_field_count",
    "attributed_operand_count",
    "unattributed_operand_count",
    "operand_attribution_status",
)


def render_candidate_coverage_csv(inventory: RSSInventory) -> str:
    """Report candidate attribution without claiming instruction completeness."""

    candidates_by_rung: dict[
        tuple[int | None, int | None],
        list[RSSProgramInstructionCandidateEvidence],
    ] = defaultdict(list)
    for candidate in inventory["program_files"]["instruction_candidates"]:
        candidates_by_rung[
            (candidate["program_file_number"], candidate["rung_index"])
        ].append(candidate)

    operand_offsets_by_rung: dict[tuple[int | None, int | None], set[int]] = (
        defaultdict(set)
    )
    for operand in inventory["program_files"]["operands"]:
        operand_offsets_by_rung[
            (operand["program_file_number"], operand["rung_index"])
        ].add(operand["offset"])

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for rung in inventory["program_files"]["rung_records"]:
        key = (rung["program_file_number"], rung["rung_index"])
        candidates = candidates_by_rung.get(key, [])
        recovered_offsets = operand_offsets_by_rung.get(key, set())
        candidate_field_offsets = {
            operand["offset"]
            for candidate in candidates
            for operand in candidate["operands"]
        }
        attributed = len(recovered_offsets & candidate_field_offsets)
        unattributed = len(recovered_offsets) - attributed
        if not recovered_offsets:
            status = "no_recovered_operands"
        elif not attributed:
            status = "none_attributed"
        elif unattributed:
            status = "partially_attributed"
        else:
            status = "all_recovered_operands_attributed"
        writer.writerow(
            {
                "program_file_number": rung["program_file_number"],
                "program_file_name": rung["program_file_name"] or "",
                "program_file_name_sha256": rung["program_file_name_sha256"],
                "rung_index": rung["rung_index"],
                "recovered_operand_count": len(recovered_offsets),
                "candidate_instruction_count": len(candidates),
                "candidate_field_count": sum(
                    len(candidate["operands"]) for candidate in candidates
                ),
                "attributed_operand_count": attributed,
                "unattributed_operand_count": unattributed,
                "operand_attribution_status": status,
            }
        )
    return stream.getvalue()
