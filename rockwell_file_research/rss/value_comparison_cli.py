"""Command-line comparison of corroborated RSS data-file values."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from rockwell_file_research.integration.configuration_impact import (
    configuration_address_impact,
    load_cross_reference,
)
from rockwell_file_research.rss.inventory import inventory_rss
from rockwell_file_research.rss.value_comparison import (
    compare_data_values,
    render_data_value_comparison_csv,
    render_data_value_comparison_markdown,
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
        "--markdown-output",
        type=Path,
        help="optional engineer-readable Markdown comparison report",
    )
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
        "--left-cross-reference",
        type=Path,
        help="optional PLC-HMI cross-reference JSON for the left project",
    )
    parser.add_argument(
        "--right-cross-reference",
        type=Path,
        help="optional PLC-HMI cross-reference JSON for the right project",
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
        left_cross_reference = (
            None
            if args.left_cross_reference is None
            else load_cross_reference(args.left_cross_reference)
        )
        right_cross_reference = (
            None
            if args.right_cross_reference is None
            else load_cross_reference(args.right_cross_reference)
        )
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    left_impacts = (
        None
        if left_cross_reference is None
        else {
            item.address: configuration_address_impact(
                left_cross_reference, item.address
            )
            for item in comparisons
        }
    )
    right_impacts = (
        None
        if right_cross_reference is None
        else {
            item.address: configuration_address_impact(
                right_cross_reference, item.address
            )
            for item in comparisons
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_data_value_comparison_csv(
        comparisons,
        left_profile=left_profile,
        right_profile=right_profile,
        semantic_only=args.semantic_only,
        left_impacts=left_impacts,
        right_impacts=right_impacts,
    )
    args.output.write_text(rendered, encoding="utf-8")
    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(
            render_data_value_comparison_markdown(
                comparisons,
                left_profile=left_profile,
                right_profile=right_profile,
                semantic_only=args.semantic_only,
                left_impacts=left_impacts,
                right_impacts=right_impacts,
            ),
            encoding="utf-8",
        )
    output_rows = max(0, rendered.count("\n") - 1)
    print(
        f"Wrote {output_rows} comparison rows from "
        f"{len(comparisons)} decoded addresses to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
