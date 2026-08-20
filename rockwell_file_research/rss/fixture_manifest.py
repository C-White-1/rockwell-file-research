"""Validate controlled RSS instruction-fixture delivery packages."""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

REQUIRED_COLUMNS = (
    "fixture_id",
    "parent_fixture",
    "filename",
    "sha256",
    "project_name",
    "rslogix_product",
    "rslogix_version",
    "controller_catalog",
    "controller_series",
    "controller_revision",
    "program_file",
    "displayed_rung_number",
    "intended_change",
    "displayed_source",
    "verified",
    "created_at",
    "creator",
    "online_state",
    "publishable",
    "notes",
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_BOOLEANS = frozenset({"true", "false"})


@dataclass(frozen=True)
class ManifestIssue:
    """One actionable manifest validation failure."""

    message: str
    row: int | None = None

    def __str__(self) -> str:
        prefix = f"row {self.row}: " if self.row is not None else ""
        return f"{prefix}{self.message}"


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_rss_path(package: Path, value: str) -> Path | None:
    relative = PurePosixPath(value.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".rss":
        return None
    candidate = (package / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(package.resolve())
    except ValueError:
        return None
    return candidate


def _valid_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _cycle_members(parents: Mapping[str, str]) -> set[str]:
    cyclic: set[str] = set()
    for start in parents:
        path: list[str] = []
        positions: dict[str, int] = {}
        current = start
        while current and current in parents:
            if current in positions:
                cyclic.update(path[positions[current] :])
                break
            positions[current] = len(path)
            path.append(current)
            current = parents[current]
    return cyclic


def validate_fixture_manifest(manifest: Path) -> list[ManifestIssue]:
    """Return every detected contract violation without reading RSS internals."""

    if not manifest.is_file():
        return [ManifestIssue(f"manifest does not exist: {manifest}")]
    package = manifest.parent
    with manifest.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in columns]
        if missing:
            return [ManifestIssue(f"missing required columns: {', '.join(missing)}")]
        rows = [(number, dict(row)) for number, row in enumerate(reader, start=2)]

    issues: list[ManifestIssue] = []
    ids: dict[str, int] = {}
    filenames: dict[str, int] = {}
    parents: dict[str, str] = {}
    required_values = tuple(column for column in REQUIRED_COLUMNS if column not in {"parent_fixture", "notes"})

    for number, row in rows:
        for column in required_values:
            if not (row.get(column) or "").strip():
                issues.append(ManifestIssue(f"{column} is required", number))
        fixture_id = (row.get("fixture_id") or "").strip()
        parent = (row.get("parent_fixture") or "").strip()
        filename = (row.get("filename") or "").strip()
        if fixture_id in ids:
            issues.append(ManifestIssue(f"duplicate fixture_id {fixture_id!r} (first seen on row {ids[fixture_id]})", number))
        elif fixture_id:
            ids[fixture_id] = number
            parents[fixture_id] = parent
        if filename in filenames:
            issues.append(ManifestIssue(f"duplicate filename {filename!r} (first seen on row {filenames[filename]})", number))
        elif filename:
            filenames[filename] = number

        source = _safe_rss_path(package, filename)
        if source is None:
            issues.append(ManifestIssue("filename must be a safe relative .rss path", number))
        else:
            if fixture_id and source.stem != fixture_id:
                issues.append(ManifestIssue("fixture_id must equal the RSS filename stem", number))
            if not source.is_file():
                issues.append(ManifestIssue(f"RSS file does not exist: {filename}", number))
            else:
                expected = (row.get("sha256") or "").strip()
                if _SHA256.fullmatch(expected) and _digest(source) != expected:
                    issues.append(ManifestIssue("sha256 does not match the RSS file", number))

        sha256 = (row.get("sha256") or "").strip()
        if sha256 and not _SHA256.fullmatch(sha256):
            issues.append(ManifestIssue("sha256 must be 64 lowercase hexadecimal characters", number))
        for column in ("verified", "publishable"):
            value = (row.get(column) or "").strip()
            if value and value not in _BOOLEANS:
                issues.append(ManifestIssue(f"{column} must be true or false", number))
        timestamp = (row.get("created_at") or "").strip()
        if timestamp and not _valid_timestamp(timestamp):
            issues.append(ManifestIssue("created_at must be an ISO 8601 timestamp with a UTC offset", number))
        state = (row.get("online_state") or "").strip()
        if state and state != "offline":
            issues.append(ManifestIssue("online_state must be offline", number))

    roots = [fixture_id for fixture_id, parent in parents.items() if not parent]
    if len(roots) != 1:
        issues.append(ManifestIssue(f"manifest must contain exactly one root fixture; found {len(roots)}"))
    for fixture_id, parent in parents.items():
        if parent and parent not in ids:
            issues.append(ManifestIssue(f"fixture {fixture_id!r} references unknown parent {parent!r}", ids[fixture_id]))
    for fixture_id in sorted(_cycle_members(parents)):
        issues.append(ManifestIssue(f"fixture {fixture_id!r} participates in a parent cycle", ids[fixture_id]))
    return issues
