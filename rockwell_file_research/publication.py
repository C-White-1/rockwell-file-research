"""Prevent private industrial artifacts from entering repository history."""

from __future__ import annotations

import argparse
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path, PurePosixPath

PRIVATE_ROOTS = frozenset(
    {
        "cha-experiments",
        "outputs",
        "private-fixtures",
        "private-outputs",
        "Project5",
        "PV800_PumpControl_V2.1",
        "src",
    }
)
PROHIBITED_SUFFIXES = frozenset(
    {
        ".7z",
        ".acd",
        ".acfproj",
        ".cha",
        ".ccwsln",
        ".ccwsuo",
        ".docx",
        ".dwg",
        ".pdf",
        ".pvc",
        ".rss",
        ".xlsx",
    }
)


class PublicationCheckError(RuntimeError):
    """Git paths could not be inspected."""


def prohibited_paths(paths: Iterable[str]) -> list[str]:
    """Return tracked paths that violate the repository publication policy."""

    violations: list[str] = []
    for raw_path in paths:
        normalized = raw_path.replace("\\", "/")
        path = PurePosixPath(normalized)
        if not path.parts:
            continue
        in_private_root = path.parts[0] in PRIVATE_ROOTS
        has_prohibited_suffix = path.suffix.lower() in PROHIBITED_SUFFIXES
        if in_private_root or has_prohibited_suffix:
            violations.append(normalized)
    return sorted(set(violations))


def tracked_paths(repository: Path) -> list[str]:
    """Read tracked and staged paths directly from the Git index."""

    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode(errors="replace").strip()
        raise PublicationCheckError(f"could not inspect Git index: {message}")
    return [
        item.decode(errors="surrogateescape")
        for item in completed.stdout.split(b"\0")
        if item
    ]


def check_repository(repository: Path) -> list[str]:
    """Return publication-policy violations from a repository's Git index."""

    return prohibited_paths(tracked_paths(repository))


def build_parser() -> argparse.ArgumentParser:
    """Create the publication-check command parser."""

    parser = argparse.ArgumentParser(
        description="Fail if private industrial artifacts are tracked by Git."
    )
    parser.add_argument(
        "repository",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="repository to inspect (default: current directory)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the publication guard."""

    args = build_parser().parse_args(argv)
    try:
        violations = check_repository(args.repository)
    except PublicationCheckError as error:
        print(f"Publication check failed: {error}")
        return 2
    if violations:
        print("Publication check failed; prohibited tracked paths:")
        for path in violations:
            print(f"- {path}")
        return 1
    print("Publication check passed; no prohibited artifacts are tracked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
