"""Render decoded RSS rung-comment attachments as deterministic CSV."""

import csv
import io

from rockwell_file_research.rss.models import RSSInventory

FIELDNAMES = [
    "attachment_kind",
    "attachment_source",
    "attachment_key",
    "program_file_number",
    "rung_index",
    "address",
    "attachment_status",
    "comment",
    "comment_sha256",
    "byte_length",
    "text_offset",
    "key_offset",
]


def render_rung_comment_csv(inventory: RSSInventory) -> str:
    """Render one row per MEM DATABASE rung-comment attachment."""

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    for record in inventory["rung_comments"]["records"]:
        writer.writerow(
            {
                "attachment_kind": record["attachment_kind"],
                "attachment_source": record["attachment_source"],
                "attachment_key": record["attachment_key"],
                "program_file_number": record["program_file_number"],
                "rung_index": record["rung_index"],
                "address": record["address"] or "",
                "attachment_status": (
                    "corroborated"
                    if record["program_rung_corroborated"]
                    else (
                        "address_attached"
                        if record["attachment_kind"] == "address"
                        else "uncorroborated"
                    )
                ),
                "comment": record["text"] or "",
                "comment_sha256": record["sha256"],
                "byte_length": record["length"],
                "text_offset": record["text_offset"],
                "key_offset": record["key_offset"],
            }
        )
    return stream.getvalue()
