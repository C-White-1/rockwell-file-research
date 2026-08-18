"""Build and serialize PLC–HMI cross-reference evidence."""

import json
from pathlib import Path

from rockwell_file_research.ccw.reporting import build_report
from rockwell_file_research.integration.cross_reference import (
    build_plc_hmi_cross_reference,
)
from rockwell_file_research.integration.models import PLCHMICrossReference
from rockwell_file_research.rss.inventory import inventory_rss


def export_plc_hmi_cross_reference(
    hmi_source: Path,
    plc_source: Path,
    destination: Path,
    *,
    hmi_source_label: str | None = None,
    plc_source_label: str | None = None,
    include_private_text: bool = False,
) -> PLCHMICrossReference:
    """Parse both sources and write one deterministic cross-reference."""

    hmi = build_report(hmi_source, source_label=hmi_source_label)
    plc = inventory_rss(
        plc_source,
        source_label=plc_source_label,
        include_private_text=include_private_text,
    )
    result = build_plc_hmi_cross_reference(
        hmi,
        plc,
        include_private_text=include_private_text,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result
