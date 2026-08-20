"""Command-line validation for controlled RSS fixture packages."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.rss.fixture_manifest import validate_fixture_manifest


def build_parser() -> argparse.ArgumentParser:
    """Create the controlled-fixture validator parser."""

    parser = argparse.ArgumentParser(
        description="Validate an RSS controlled-fixture manifest and its local files."
    )
    parser.add_argument("manifest", type=Path, help="path to manifest.csv")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate a package and return a process-friendly status code."""

    args = build_parser().parse_args(argv)
    issues = validate_fixture_manifest(args.manifest)
    if issues:
        print(f"RSS controlled-fixture validation failed ({len(issues)} issue(s)):")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("RSS controlled-fixture validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
