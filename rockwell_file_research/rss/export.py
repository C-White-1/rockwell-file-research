"""Serialize RSS structural evidence without exporting project payloads."""

import json
from pathlib import Path

from rockwell_file_research.rss.inventory import inventory_rss
from rockwell_file_research.rss.models import RSSInventory


def export_inventory(
    source: Path,
    destination: Path,
    *,
    source_label: str | None = None,
    include_private_text: bool = False,
) -> RSSInventory:
    """Write one deterministic RSS inventory JSON document."""

    inventory = inventory_rss(
        source,
        source_label=source_label,
        include_private_text=include_private_text,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return inventory
