"""Command-line interface for read-only RSS structural inventorying."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.rss.errors import RSSInventoryError
from rockwell_file_research.rss.export import export_inventory


def build_parser() -> argparse.ArgumentParser:
    """Create the RSS inventory command parser."""

    parser = argparse.ArgumentParser(
        description="Inventory an RSLogix 500 RSS OLE container without exporting payloads."
    )
    parser.add_argument("source", type=Path, help="RSLogix 500 RSS project")
    parser.add_argument(
        "--output", type=Path, required=True, help="inventory JSON file"
    )
    parser.add_argument(
        "--source-label",
        help="neutral source identifier stored instead of the RSS filename",
    )
    parser.add_argument(
        "--operand-csv-output",
        type=Path,
        help="optional aggregate CSV listing every recovered ladder operand",
    )
    parser.add_argument(
        "--include-private-text",
        action="store_true",
        help="include decoded PROCESSOR text; keep the output private",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the RSS inventory command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.source.is_file():
        parser.error(f"source project does not exist: {args.source}")
    try:
        inventory = export_inventory(
            args.source,
            args.output,
            source_label=args.source_label,
            include_private_text=args.include_private_text,
            operand_csv_destination=args.operand_csv_output,
        )
    except RSSInventoryError as error:
        parser.error(str(error))
    present = sum(section["present"] for section in inventory["recognized_sections"])
    print(
        f"Inventoried {len(inventory['streams'])} streams and "
        f"{present} recognized sections to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
