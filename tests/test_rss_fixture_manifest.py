"""Tests for the controlled RSS fixture manifest contract."""

import csv
import hashlib
from pathlib import Path

from rockwell_file_research.rss.fixture_cli import main
from rockwell_file_research.rss.fixture_manifest import (
    REQUIRED_COLUMNS,
    validate_fixture_manifest,
)


def _write_package(root: Path, rows: list[dict[str, str]]) -> Path:
    for row in rows:
        source = root / row["filename"]
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(row.pop("payload").encode())
        row["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = root / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter[str](stream, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return manifest


def _row(fixture_id: str, parent: str = "") -> dict[str, str]:
    return {
        "fixture_id": fixture_id,
        "parent_fixture": parent,
        "filename": f"rss/{fixture_id}.rss",
        "sha256": "",
        "project_name": "ControlledFixture",
        "rslogix_product": "RSLogix 500",
        "rslogix_version": "12.00",
        "controller_catalog": "1763-L16BWA",
        "controller_series": "B",
        "controller_revision": "16",
        "program_file": "LAD 2",
        "displayed_rung_number": "0",
        "intended_change": "Add one XIC",
        "displayed_source": "XIC B3:0/0",
        "verified": "true",
        "created_at": "2026-08-20T12:00:00+10:00",
        "creator": "fixture-engineer",
        "online_state": "offline",
        "publishable": "false",
        "notes": "synthetic test fixture",
        "payload": fixture_id,
    }


def test_valid_manifest_and_cli_pass(tmp_path: Path, capsys: object) -> None:
    manifest = _write_package(tmp_path, [_row("00_base"), _row("01_xic", "00_base")])

    assert validate_fixture_manifest(manifest) == []
    assert main([str(manifest)]) == 0


def test_detects_digest_path_metadata_and_parent_failures(tmp_path: Path) -> None:
    child = _row("01_xic", "missing")
    child["filename"] = "../01_xic.rss"
    child["verified"] = "yes"
    child["created_at"] = "2026-08-20"
    child["online_state"] = "online"
    manifest = _write_package(tmp_path, [_row("00_base"), child])
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    rows[0]["sha256"] = "0" * 64
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter[str](stream, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    messages = [str(issue) for issue in validate_fixture_manifest(manifest)]

    assert any("sha256 does not match" in message for message in messages)
    assert any("safe relative .rss" in message for message in messages)
    assert any("verified must be true or false" in message for message in messages)
    assert any("ISO 8601" in message for message in messages)
    assert any("online_state must be offline" in message for message in messages)
    assert any("unknown parent" in message for message in messages)


def test_detects_duplicate_ids_and_parent_cycles(tmp_path: Path) -> None:
    first = _row("00_base", "01_xic")
    second = _row("01_xic", "00_base")
    duplicate = _row("01_xic", "00_base")
    duplicate["filename"] = "rss/01_xic_copy.rss"
    manifest = _write_package(tmp_path, [first, second, duplicate])

    messages = [str(issue) for issue in validate_fixture_manifest(manifest)]

    assert any("duplicate fixture_id" in message for message in messages)
    assert any("parent cycle" in message for message in messages)
    assert any("exactly one root" in message for message in messages)
