"""Tests for privacy-preserving RSS structural inventorying."""

from datetime import UTC, datetime

import pytest

from rockwell_file_research.rss.container import (
    CompoundMetadata,
    verify_ole_signature,
)
from rockwell_file_research.rss.errors import RSSInventoryError
from rockwell_file_research.rss.inventory import build_inventory


class SyntheticCompoundDocument:
    """In-memory clean-room compound document used instead of vendor files."""

    def __init__(self) -> None:
        self._streams = {
            "PROCESSOR/ObjectData": b"synthetic processor evidence",
            "PROGRAM FILES/ObjectData": b"synthetic program evidence",
            "Synthetic Extension/ObjectData": b"preserve unknown evidence",
        }

    def stream_paths(self) -> list[str]:
        return list(reversed(self._streams))

    def storage_paths(self) -> list[str]:
        return ["Synthetic Extension", "PROGRAM FILES", "PROCESSOR"]

    def read_stream(self, path: str) -> bytes:
        return self._streams[path]

    def metadata(self) -> CompoundMetadata:
        return CompoundMetadata(
            creating_application="Synthetic RSLogix-like Writer",
            created_at=datetime(2026, 8, 19, 1, 2, 3, tzinfo=UTC),
            last_saved_at=datetime(2026, 8, 19, 4, 5, 6, tzinfo=UTC),
        )


def test_inventory_preserves_unknown_streams_without_payload_export(tmp_path) -> None:
    source = tmp_path / "Customer A" / "Secret Pump.rss"
    source.parent.mkdir()
    source.write_bytes(b"synthetic source container")

    inventory = build_inventory(
        source,
        SyntheticCompoundDocument(),
        source_label="fixture-001",
    )

    assert inventory["source"]["reference"] == "fixture-001"
    assert inventory["source"]["size"] == len(b"synthetic source container")
    assert inventory["compound_metadata"]["creating_application"] == (
        "Synthetic RSLogix-like Writer"
    )
    assert inventory["unrecognized_streams"] == ["Synthetic Extension/ObjectData"]
    assert inventory["streams"] == sorted(
        inventory["streams"], key=lambda stream: stream["path"]
    )
    serialized = repr(inventory)
    assert "Customer A" not in serialized
    assert "Secret Pump.rss" not in serialized
    assert "synthetic program evidence" not in serialized
    assert all(len(stream["sha256"]) == 64 for stream in inventory["streams"])
    assert inventory["processor"]["private_text_included"] is False
    assert all(
        region["text"] is None for region in inventory["processor"]["text_regions"]
    )


def test_missing_recognized_sections_are_explicit(tmp_path) -> None:
    source = tmp_path / "synthetic.rss"
    source.write_bytes(b"source")

    inventory = build_inventory(source, SyntheticCompoundDocument())
    sections = {
        section["name"]: section for section in inventory["recognized_sections"]
    }

    assert sections["PROCESSOR"]["present"] is True
    assert sections["PROGRAM FILES"]["present"] is True
    assert sections["DATA FILES"] == {
        "name": "DATA FILES",
        "stream_path": "DATA FILES/ObjectData",
        "present": False,
        "size": 0,
        "sha256": "",
    }


def test_non_ole_source_is_rejected(tmp_path) -> None:
    source = tmp_path / "not-an-rss.rss"
    source.write_bytes(b"not an OLE file")

    with pytest.raises(RSSInventoryError, match="not an OLE compound file"):
        verify_ole_signature(source)


def test_private_processor_text_requires_explicit_opt_in(tmp_path) -> None:
    source = tmp_path / "synthetic.rss"
    source.write_bytes(b"source")

    inventory = build_inventory(
        source,
        SyntheticCompoundDocument(),
        include_private_text=True,
    )

    processor = inventory["processor"]
    assert processor["private_text_included"] is True
    assert processor["text_regions"] == [
        {
            "classification": "project_identifier_candidate",
            "offset": 0,
            "length": len(b"synthetic processor evidence"),
            "sha256": processor["text_regions"][0]["sha256"],
            "text": "synthetic processor evidence",
        }
    ]
