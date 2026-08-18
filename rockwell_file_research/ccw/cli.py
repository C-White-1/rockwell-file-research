"""Command-line interface for CCW report extraction."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.ccw.errors import CCWReportError
from rockwell_file_research.ccw.export import export_report


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Extract structured evidence from a CCW PanelView XLSX report."
    )
    parser.add_argument("source", type=Path, help="CCW-generated XLSX report")
    parser.add_argument("--output", type=Path, required=True, help="output directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CCW report command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.source.is_file():
        parser.error(f"source report does not exist: {args.source}")
    try:
        report = export_report(args.source, args.output)
    except CCWReportError as error:
        parser.error(str(error))
    summary = report["summary"]
    print(
        f"Extracted {summary['external_tag_count']} tags, "
        f"{summary['screen_count']} screens, "
        f"{summary['screen_object_count']} objects, and "
        f"{summary['alarm_count']} alarms to {args.output}"
    )
    return 0
