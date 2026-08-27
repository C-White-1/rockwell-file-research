"""Command-line interface for read-only CCW archive inventorying."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.ccw.archive import (
    CCWArchiveError,
    inspect_ccwarc,
    write_inventory,
)
from rockwell_file_research.ccw.archive_markdown import render_ccw_archive_markdown
from rockwell_file_research.ccw.cross_reference import build_cross_reference


def main(argv: Sequence[str] | None = None) -> int:
    """Inventory a CCW archive and optionally write JSON evidence."""

    parser = argparse.ArgumentParser(description="Inventory a CCW .ccwarc archive.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--source-label")
    args = parser.parse_args(argv)
    try:
        inventory = inspect_ccwarc(args.source)
    except CCWArchiveError as error:
        parser.error(str(error))
    if args.output:
        write_inventory(inventory, args.output)
    if args.markdown_output:
        report = build_cross_reference(args.source)
        args.markdown_output.write_text(
            render_ccw_archive_markdown(
                inventory, report, source_label=args.source_label
            ),
            encoding="utf-8",
        )
    print(
        f"CCW {inventory.ccw_version or '?'} project "
        f"{inventory.project_name or '?'}: {inventory.entry_count} entries, "
        f"{len(inventory.programs)} programs"
    )
    if inventory.sensitive_entries:
        print(f"Privacy warning: {len(inventory.sensitive_entries)} sensitive entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
