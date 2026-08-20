"""Command-line interface for PLC–HMI cross-reference generation."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.integration.export import (
    export_plc_hmi_cross_reference,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the cross-reference command parser."""

    parser = argparse.ArgumentParser(
        description="Resolve PanelView tag addresses against an RSS data-file catalogue."
    )
    parser.add_argument("hmi_source", type=Path, help="CCW-generated XLSX report")
    parser.add_argument("plc_source", type=Path, help="RSLogix 500 RSS project")
    parser.add_argument("--output", type=Path, required=True, help="output JSON file")
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="optional human-readable Markdown report",
    )
    parser.add_argument(
        "--rung-csv-output",
        type=Path,
        help="optional exact and contained-bit rung evidence CSV",
    )
    parser.add_argument("--hmi-source-label", help="neutral HMI source identifier")
    parser.add_argument("--plc-source-label", help="neutral PLC source identifier")
    parser.add_argument(
        "--include-private-text",
        action="store_true",
        help="include tag names, addresses, and RSS record names; keep output private",
    )
    parser.add_argument(
        "--omit-hashes",
        action="store_true",
        help="omit SHA-256 fields from a human-readable private copy",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the cross-reference command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.hmi_source.is_file():
        parser.error(f"HMI report does not exist: {args.hmi_source}")
    if not args.plc_source.is_file():
        parser.error(f"PLC project does not exist: {args.plc_source}")
    result = export_plc_hmi_cross_reference(
        args.hmi_source,
        args.plc_source,
        args.output,
        hmi_source_label=args.hmi_source_label,
        plc_source_label=args.plc_source_label,
        include_private_text=args.include_private_text,
        omit_hashes=args.omit_hashes,
        markdown_destination=args.markdown_output,
        rung_csv_destination=args.rung_csv_output,
    )
    summary = result["summary"]
    print(
        f"Resolved {summary['resolved_count']} of {summary['address_count']} "
        f"HMI addresses to RSS data files in {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
