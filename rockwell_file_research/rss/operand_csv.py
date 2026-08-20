"""Aggregate all recovered RSS ladder operand strings as CSV evidence."""

import csv
import io
from collections import defaultdict

from rockwell_file_research.rss.models import RSSInventory, RSSProgramOperandEvidence

FIELDNAMES: list[str] = [
    "operand",
    "operand_sha256",
    "occurrence_count",
    "direct_occurrence_count",
    "indirect_occurrence_count",
    "program_file_count",
    "distinct_rung_count",
    "program_files",
    "rung_locations",
]


def render_operand_inventory_csv(inventory: RSSInventory) -> str:
    """Render one deterministic aggregate row per exact source operand string."""

    grouped: dict[str, list[RSSProgramOperandEvidence]] = defaultdict(list)
    for occurrence in inventory["program_files"]["operands"]:
        grouped[occurrence["sha256"]].append(occurrence)

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    rows: list[dict[str, object]] = []
    for operand_sha256, occurrences in grouped.items():
        first = occurrences[0]
        program_files = {
            (
                occurrence["program_file_number"],
                occurrence["program_file_name"]
                or occurrence["program_file_name_sha256"]
                or "-",
            )
            for occurrence in occurrences
            if occurrence["program_file_number"] is not None
        }
        rung_locations = {
            (occurrence["program_file_number"], occurrence["rung_index"])
            for occurrence in occurrences
            if occurrence["program_file_number"] is not None
            and occurrence["rung_index"] is not None
        }
        rows.append(
            {
                "operand": first["operand"] or "",
                "operand_sha256": operand_sha256,
                "occurrence_count": len(occurrences),
                "direct_occurrence_count": sum(
                    not occurrence["indirect"] for occurrence in occurrences
                ),
                "indirect_occurrence_count": sum(
                    occurrence["indirect"] for occurrence in occurrences
                ),
                "program_file_count": len(program_files),
                "distinct_rung_count": len(rung_locations),
                "program_files": "; ".join(
                    f"{number} {name}" for number, name in sorted(program_files)
                ),
                "rung_locations": "; ".join(
                    f"{number}:{rung}" for number, rung in sorted(rung_locations)
                ),
            }
        )
    rows.sort(key=lambda row: str(row["operand"] or row["operand_sha256"]))
    writer.writerows(rows)
    return stream.getvalue()
