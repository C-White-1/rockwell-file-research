"""Compose loss-preserving CCW evidence reports."""

import hashlib
from collections import Counter
from pathlib import Path

from rockwell_file_research.ccw import normalize
from rockwell_file_research.ccw.models import CCWReport
from rockwell_file_research.ccw.validation import validate_workbook
from rockwell_file_research.ccw.xlsx import read_workbook


def build_report(path: Path) -> CCWReport:
    """Build normalized views while retaining every non-empty source cell."""

    sheets = read_workbook(path)
    diagnostics = validate_workbook(sheets)
    tags = normalize.tags(sheets)
    screens, objects = normalize.screens(sheets)
    alarms = normalize.alarms(sheets)
    return {
        "schema_version": "rockwell-file-research.ccw-report.v1",
        "source": {
            "path": str(path),
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
        "application": normalize.application(sheets),
        "summary": {
            "external_tag_count": len(tags),
            "tag_types": dict(Counter(tag["data_type"] for tag in tags)),
            "screen_count": len(screens),
            "screen_object_count": len(objects),
            "alarm_count": len(alarms),
        },
        "communications": normalize.communications(sheets),
        "diagnostics": diagnostics,
        "tags": tags,
        "screens": screens,
        "screen_objects": objects,
        "alarms": alarms,
        "raw_sheets": sheets,
    }
