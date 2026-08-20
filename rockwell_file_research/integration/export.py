"""Build and serialize PLC–HMI cross-reference evidence."""

import json
from pathlib import Path

from rockwell_file_research.ccw.reporting import build_report
from rockwell_file_research.integration.cross_reference import (
    build_plc_hmi_cross_reference,
)
from rockwell_file_research.integration.markdown import (
    render_cross_reference_markdown,
)
from rockwell_file_research.integration.models import PLCHMICrossReference
from rockwell_file_research.integration.rung_csv import render_rung_usage_csv
from rockwell_file_research.rss.inventory import inventory_rss


def _omit_sha256_fields(value: object) -> object:
    """Return a JSON-compatible copy without integrity-hash fields."""

    if isinstance(value, dict):
        return {
            key: _omit_sha256_fields(item)
            for key, item in value.items()
            if not key.endswith(("sha256", "sha256s"))
        }
    if isinstance(value, list):
        return [_omit_sha256_fields(item) for item in value]
    return value


def export_plc_hmi_cross_reference(
    hmi_source: Path,
    plc_source: Path,
    destination: Path,
    *,
    hmi_source_label: str | None = None,
    plc_source_label: str | None = None,
    include_private_text: bool = False,
    omit_hashes: bool = False,
    markdown_destination: Path | None = None,
    rung_csv_destination: Path | None = None,
) -> PLCHMICrossReference:
    """Parse both sources and write one deterministic cross-reference."""

    hmi = build_report(hmi_source, source_label=hmi_source_label)
    plc = inventory_rss(
        plc_source,
        source_label=plc_source_label,
        # Operand text is needed transiently for address correlation. The
        # composed report applies its own explicit privacy boundary.
        include_private_text=True,
    )
    result = build_plc_hmi_cross_reference(
        hmi,
        plc,
        include_private_text=include_private_text,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized: object = _omit_sha256_fields(result) if omit_hashes else result
    destination.write_text(
        json.dumps(serialized, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if markdown_destination is not None:
        markdown_destination.parent.mkdir(parents=True, exist_ok=True)
        markdown_destination.write_text(
            render_cross_reference_markdown(result), encoding="utf-8"
        )
    if rung_csv_destination is not None:
        rung_csv_destination.parent.mkdir(parents=True, exist_ok=True)
        rung_csv_destination.write_text(
            render_rung_usage_csv(result, omit_hashes=omit_hashes),
            encoding="utf-8",
        )
    return result
