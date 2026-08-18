"""Serialize normalized CCW evidence to JSON and CSV."""

import csv
import json
from pathlib import Path
from typing import Any

from rockwell_file_research.ccw.reporting import build_report


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write rows using the ordered union of all encountered fields."""

    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        if fieldnames:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def export_report(source: Path, destination: Path) -> dict[str, Any]:
    """Export JSON and CSV evidence derived from a CCW report."""

    report = build_report(source)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_csv(destination / "tags.csv", report["tags"])
    write_csv(destination / "screens.csv", report["screens"])
    write_csv(destination / "screen_objects.csv", report["screen_objects"])
    write_csv(destination / "alarms.csv", report["alarms"])
    return report
