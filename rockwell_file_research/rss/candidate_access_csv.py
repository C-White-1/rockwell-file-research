"""Privacy-aware CSV rendering for probable RSS instruction access."""

import csv
import io

from rockwell_file_research.rss.models import RSSInventory

FIELDNAMES = (
    "proposed_mnemonic",
    "confidence",
    "access",
    "role",
    "address_family",
    "operand",
    "operand_sha256",
    "program_file_number",
    "program_file_name",
    "program_file_name_sha256",
    "rung_index",
    "rung_start_offset",
    "rung_end_offset",
    "selector_hex",
    "selector_offset",
    "evidence_profile",
    "diagnostics",
)


def render_instruction_candidate_access_csv(inventory: RSSInventory) -> str:
    """Render one row per probable instruction operand without unredacting it."""

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for candidate in inventory["program_files"]["instruction_candidates"]:
        for operand in candidate["operands"]:
            writer.writerow(
                {
                    "proposed_mnemonic": candidate["proposed_mnemonic"],
                    "confidence": candidate["confidence"],
                    "access": operand["access"],
                    "role": operand["role"],
                    "address_family": operand["address_family"],
                    "operand": operand["value"] or "",
                    "operand_sha256": operand["sha256"],
                    "program_file_number": candidate["program_file_number"],
                    "program_file_name": candidate["program_file_name"] or "",
                    "program_file_name_sha256": (
                        candidate["program_file_name_sha256"] or ""
                    ),
                    "rung_index": candidate["rung_index"],
                    "rung_start_offset": candidate["rung_start_offset"],
                    "rung_end_offset": candidate["rung_end_offset"],
                    "selector_hex": f"0x{candidate['selector']:02X}",
                    "selector_offset": candidate["selector_offset"],
                    "evidence_profile": candidate["evidence_profile"],
                    "diagnostics": " | ".join(candidate["diagnostics"]),
                }
            )
    return stream.getvalue()
