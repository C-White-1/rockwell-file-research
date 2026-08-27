"""Command-line interface for read-only CCW archive inventorying."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.ccw.archive import (
    CCWArchiveError,
    inspect_ccwarc,
    write_inventory,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Inventory a CCW archive and optionally write JSON evidence."""

    parser = argparse.ArgumentParser(description="Inventory a CCW .ccwarc archive.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        inventory = inspect_ccwarc(args.source)
    except CCWArchiveError as error:
        parser.error(str(error))
    if args.output:
        write_inventory(inventory, args.output)
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
