"""Serialize RSS structural evidence without exporting project payloads."""

import json
from pathlib import Path

from rockwell_file_research.rss.data_value_csv import render_data_value_csv
from rockwell_file_research.rss.inventory import inventory_rss
from rockwell_file_research.rss.models import RSSInventory
from rockwell_file_research.rss.operand_csv import render_operand_inventory_csv
from rockwell_file_research.rss.rung_comment_csv import render_rung_comment_csv


def export_inventory(
    source: Path,
    destination: Path,
    *,
    source_label: str | None = None,
    include_private_text: bool = False,
    include_private_values: bool = False,
    operand_csv_destination: Path | None = None,
    rung_comment_csv_destination: Path | None = None,
    data_value_csv_destination: Path | None = None,
) -> RSSInventory:
    """Write one deterministic RSS inventory JSON document."""

    inventory = inventory_rss(
        source,
        source_label=source_label,
        include_private_text=include_private_text,
        include_private_values=include_private_values,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if operand_csv_destination is not None:
        operand_csv_destination.parent.mkdir(parents=True, exist_ok=True)
        operand_csv_destination.write_text(
            render_operand_inventory_csv(inventory),
            encoding="utf-8",
        )
    if rung_comment_csv_destination is not None:
        rung_comment_csv_destination.parent.mkdir(parents=True, exist_ok=True)
        rung_comment_csv_destination.write_text(
            render_rung_comment_csv(inventory),
            encoding="utf-8",
        )
    if data_value_csv_destination is not None:
        data_value_csv_destination.parent.mkdir(parents=True, exist_ok=True)
        data_value_csv_destination.write_text(
            render_data_value_csv(inventory),
            encoding="utf-8",
        )
    return inventory
