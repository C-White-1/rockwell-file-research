"""Command-line comparison of corroborated RSS data-file values."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.rss.inventory import inventory_rss
from rockwell_file_research.rss.value_comparison import (
    compare_data_values,
    render_data_value_comparison_csv,
)
from rockwell_file_research.rss.value_semantics import load_semantic_value_profile


def build_parser() -> argparse.ArgumentParser:
    """Create the RSS value-comparison parser."""

    parser = argparse.ArgumentParser(
        description="Compare corroborated data-file values from two RSS projects."
    )
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--left-semantic-profile",
        type=Path,
        help="optional evidence-backed CSV meanings for the left project",
    )
    parser.add_argument(
        "--right-semantic-profile",
        type=Path,
        help="optional evidence-backed CSV meanings for the right project",
    )
    parser.add_argument(
        "--include-private-values",
        action="store_true",
        help="include exact decoded values; keep the output private",
    )
    parser.add_argument(
        "--semantic-only",
        action="store_true",
        help="omit addresses with no matching rule in either semantic profile",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Compare two RSS projects and write a privacy-aware CSV."""

    parser = build_parser()
    args = parser.parse_args(argv)
    for source in (args.left, args.right):
        if not source.is_file():
            parser.error(f"source project does not exist: {source}")
    left = inventory_rss(args.left, include_private_values=args.include_private_values)
    right = inventory_rss(
        args.right, include_private_values=args.include_private_values
    )
    comparisons = compare_data_values(left, right)
    try:
        left_profile = (
            None
            if args.left_semantic_profile is None
            else load_semantic_value_profile(args.left_semantic_profile)
        )
        right_profile = (
            None
            if args.right_semantic_profile is None
            else load_semantic_value_profile(args.right_semantic_profile)
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_data_value_comparison_csv(
        comparisons,
        left_profile=left_profile,
        right_profile=right_profile,
        semantic_only=args.semantic_only,
    )
    args.output.write_text(rendered, encoding="utf-8")
    output_rows = max(0, rendered.count("\n") - 1)
    print(
        f"Wrote {output_rows} comparison rows from "
        f"{len(comparisons)} decoded addresses to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
