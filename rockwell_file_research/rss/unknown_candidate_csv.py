"""Aggregate unclassified RSS instruction candidates without guessing identity."""

import csv
import io
from collections import defaultdict

from rockwell_file_research.rss.models import (
    RSSInventory,
    RSSProgramInstructionCandidateEvidence,
)

FIELDNAMES = (
    "selector_hex",
    "selector_decimal",
    "record_count",
    "operand_count_shapes",
    "address_families",
    "program_file_count",
    "rung_count",
    "evidence_profiles",
)


def render_unknown_candidate_csv(inventory: RSSInventory) -> str:
    """Render one aggregate row per unclassified selector value."""

    grouped: dict[int, list[RSSProgramInstructionCandidateEvidence]] = defaultdict(list)
    for candidate in inventory["program_files"]["instruction_candidates"]:
        if candidate["proposed_mnemonic"] == "UNKNOWN":
            grouped[candidate["selector"]].append(candidate)

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for selector, candidates in sorted(grouped.items()):
        operand_shapes = sorted({len(item["operands"]) for item in candidates})
        address_families = sorted(
            {
                operand["address_family"]
                for item in candidates
                for operand in item["operands"]
            }
        )
        program_files = {
            item["program_file_number"]
            for item in candidates
            if item["program_file_number"] is not None
        }
        rungs = {
            (item["program_file_number"], item["rung_index"])
            for item in candidates
            if item["rung_index"] is not None
        }
        writer.writerow(
            {
                "selector_hex": f"0x{selector:02X}",
                "selector_decimal": selector,
                "record_count": len(candidates),
                "operand_count_shapes": ";".join(map(str, operand_shapes)),
                "address_families": ";".join(address_families),
                "program_file_count": len(program_files),
                "rung_count": len(rungs),
                "evidence_profiles": ";".join(
                    sorted({item["evidence_profile"] for item in candidates})
                ),
            }
        )
    return stream.getvalue()
