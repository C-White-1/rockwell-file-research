"""Serialize normalized CCW evidence to JSON and CSV."""

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from rockwell_file_research.ccw.models import CCWReport
from rockwell_file_research.ccw.reporting import build_report


def write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    """Write rows using the ordered union of all encountered fields."""

    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        if fieldnames:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def _csv_rows(records: Sequence[object]) -> list[Mapping[str, str]]:
    """Adapt string-only TypedDict records at the stdlib CSV boundary."""

    return [cast(Mapping[str, str], record) for record in records]


def export_report(source: Path, destination: Path) -> CCWReport:
    """Export JSON and CSV evidence derived from a CCW report."""

    report = build_report(source)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_csv(destination / "tags.csv", _csv_rows(report["tags"]))
    write_csv(destination / "screens.csv", _csv_rows(report["screens"]))
    write_csv(
        destination / "screen_objects.csv",
        _csv_rows(report["screen_objects"]),
    )
    write_csv(destination / "alarms.csv", _csv_rows(report["alarms"]))
    return report
