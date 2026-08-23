"""Tests for privacy-preserving RSS structural inventorying."""

import csv
import io
import zlib
from datetime import UTC, datetime

import pytest

from rockwell_file_research.rss.compressed_section import decompress_section
from rockwell_file_research.rss.container import (
    CompoundMetadata,
    verify_ole_signature,
)
from rockwell_file_research.rss.errors import RSSInventoryError
from rockwell_file_research.rss.inventory import build_inventory
from rockwell_file_research.rss.operand_csv import render_operand_inventory_csv


class SyntheticCompoundDocument:
    """In-memory clean-room compound document used instead of vendor files."""

    def __init__(self) -> None:
        def envelope(payload: bytes) -> bytes:
            compressed = zlib.compress(payload)
            return (
                (2).to_bytes(4, "little")
                + (16).to_bytes(4, "little")
                + len(compressed).to_bytes(4, "little")
                + len(payload).to_bytes(4, "little")
                + compressed
            )

        def section(*, extensional: bool) -> bytes:
            description = b"synthetic private label"
            name = b"INTEGER"
            extension = b"\x02\x00\x00\x00\x00\x00" if extensional else b""
            record = (
                (0).to_bytes(2, "little")
                + bytes([len(description)])
                + description
                + bytes([len(name)])
                + name
                + bytes(4)
                + extension
                + b"\x03\x80"
                + bytes(8)
                + (14).to_bytes(2, "little")
            )
            integer_values = (123, -2)
            value_bytes = b"".join(
                value.to_bytes(2, "little", signed=True) for value in integer_values
            )
            value_header = bytes.fromhex("02 00 01 00 00 00 FF FF")
            data_file_payload = (
                b"CDataHolder\x00"
                + bytes.fromhex("03 80 07")
                + bytes(7)
                + value_header
                + value_bytes
                + record
            )
            return envelope(data_file_payload)

        self._streams = {
            "DATA FILES/ObjectData": section(extensional=False),
            "Extensional DATA FILES/ObjectData": section(extensional=True),
            "PROCESSOR/ObjectData": b"synthetic processor evidence",
            "MEM DATABASE/ObjectData": envelope(
                b"\x01\x00\x02\x00\x00\x00"
                b"\x16synthetic rung comment\x00"
                b"\x11RUNG000002-000000\x00\x00"
            ),
            "PROGRAM FILES/ObjectData": envelope(
                b"\x03\x80\x01\x00\x01\x00MAIN\x02\x00\x00"
                b"CProgHolder\x00CLadFile\x00\x07\x80\x09\x80"
                b"B3:0/0\x00#N7:1\x00synthetic rung comment"
            ),
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
    data_files = inventory["data_file_sections"][0]
    assert data_files["present"] is True
    assert data_files["compression"] == "zlib"
    assert data_files["uncompressed_size"] > 0
    assert all(region["text"] is None for region in data_files["text_regions"])
    catalogue = inventory["data_file_catalogue"]
    assert catalogue["record_count"] == 1
    assert catalogue["sections_consistent"] is True
    assert catalogue["records"][0]["file_number"] == 0
    assert catalogue["records"][0]["unknown_numeric_candidate"] == 14
    assert catalogue["records"][0]["name"] is None
    integer_values = data_files["integer_value_arrays"]
    assert integer_values[0]["file_number"] == 0
    assert integer_values[0]["element_count"] == 2
    assert integer_values[0]["values"] is None
    assert len(integer_values[0]["values_sha256"]) == 64
    assert data_files["binary_word_arrays"] == []
    program_files = inventory["program_files"]
    assert program_files["present"] is True
    assert program_files["compression"] == "zlib"
    assert len(program_files["operands"]) == 2
    assert all(operand["operand"] is None for operand in program_files["operands"])
    assert [operand["indirect"] for operand in program_files["operands"]] == [
        False,
        True,
    ]
    assert program_files["program_file_records"][0]["file_number"] == 2
    assert program_files["program_file_records"][0]["name"] is None
    assert program_files["program_file_records"][0]["rung_reference_marker_offsets"]
    assert program_files["program_file_records"][0]["declared_rung_count"] == 1
    assert program_files["program_file_records"][0]["rung_boundaries_validated"] is True
    assert program_files["rung_records"][0]["application_text_candidate_count"] == 1
    assert (
        program_files["rung_records"][0]["application_text_candidates"][0]["text"]
        is None
    )
    comments = inventory["rung_comments"]
    assert comments["present"] is True
    assert comments["compression"] == "zlib"
    assert comments["records"] == [
        {
            "attachment_kind": "file_rung",
            "attachment_source": "rslogix_file_rung",
            "attachment_key": "RUNG000002-000000",
            "program_file_number": 2,
            "rung_index": 0,
            "address": None,
            "text_offset": comments["records"][0]["text_offset"],
            "key_offset": comments["records"][0]["key_offset"],
            "length": 22,
            "sha256": comments["records"][0]["sha256"],
            "text": None,
            "program_rung_corroborated": True,
        }
    ]


def test_missing_recognized_sections_are_explicit(tmp_path) -> None:
    source = tmp_path / "synthetic.rss"
    source.write_bytes(b"source")

    inventory = build_inventory(source, SyntheticCompoundDocument())
    sections = {
        section["name"]: section for section in inventory["recognized_sections"]
    }

    assert sections["PROCESSOR"]["present"] is True
    assert sections["PROGRAM FILES"]["present"] is True
    assert sections["DATA FILES"]["present"] is True
    assert sections["Extensional DATA FILES"]["present"] is True
    assert sections["CHANNEL CONFIGURATION"] == {
        "name": "CHANNEL CONFIGURATION",
        "stream_path": "CHANNEL CONFIGURATION/ObjectData",
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
    data_regions = inventory["data_file_sections"][0]["text_regions"]
    assert [region["classification"] for region in data_regions] == [
        "serialization_class",
        "application_text_candidate",
        "standard_data_file_label",
    ]
    assert [region["text"] for region in data_regions] == [
        "CDataHolder",
        "synthetic private label",
        "INTEGER",
    ]
    record = inventory["data_file_catalogue"]["records"][0]
    assert record["description"] == "synthetic private label"
    assert record["name"] == "INTEGER"
    program_files = inventory["program_files"]
    assert [operand["operand"] for operand in program_files["operands"]] == [
        "B3:0/0",
        "#N7:1",
    ]
    assert [region["classification"] for region in program_files["text_regions"]] == [
        "application_text_candidate",
        "serialization_class",
        "serialization_class",
        "operand_candidate",
        "operand_candidate",
        "application_text_candidate",
    ]
    program_record = program_files["program_file_records"][0]
    assert program_record["name"] == "MAIN"
    assert program_record["description"] == ""
    assert program_record["declared_rung_count"] == 1
    assert program_record["rung_boundaries_validated"] is True
    assert [operand["rung_index"] for operand in program_files["operands"]] == [0, 0]
    assert all(
        operand["rung_start_offset"] is not None
        and operand["rung_end_offset"] is not None
        for operand in program_files["operands"]
    )
    assert inventory["schema_version"] == "rss-inventory/v11"
    assert program_files["instructions"] == []
    assert program_files["instruction_candidates"] == []
    assert program_files["rung_records"] == [
        {
            "program_file_number": 2,
            "program_file_name_sha256": program_record["name_sha256"],
            "program_file_name": "MAIN",
            "rung_index": 0,
            "start_offset": program_record["rung_start_offsets"][0],
            "end_offset": program_record["end_offset"],
            "byte_length": (
                program_record["end_offset"] - program_record["rung_start_offsets"][0]
            ),
            "sha256": program_files["rung_records"][0]["sha256"],
            "operand_count": 2,
            "direct_operand_count": 1,
            "indirect_operand_count": 1,
            "application_text_candidate_count": 1,
            "application_text_candidates": [
                {
                    "classification": "application_text_candidate",
                    "offset": program_files["rung_records"][0][
                        "application_text_candidates"
                    ][0]["offset"],
                    "length": len("synthetic rung comment"),
                    "sha256": program_files["rung_records"][0][
                        "application_text_candidates"
                    ][0]["sha256"],
                    "text": "synthetic rung comment",
                }
            ],
            "topology": None,
        }
    ]


def test_private_integer_values_require_independent_explicit_opt_in(tmp_path) -> None:
    source = tmp_path / "synthetic.rss"
    source.write_bytes(b"source")

    inventory = build_inventory(
        source,
        SyntheticCompoundDocument(),
        include_private_values=True,
    )

    section = inventory["data_file_sections"][0]
    assert section["private_text_included"] is False
    assert section["private_values_included"] is True
    assert section["integer_value_arrays"][0]["values"] == [123, -2]
    assert section["binary_word_arrays"] == []
    assert all(region["text"] is None for region in section["text_regions"])


def test_compressed_section_rejects_declared_length_mismatch() -> None:
    compressed = zlib.compress(b"synthetic")
    malformed = (
        (2).to_bytes(4, "little")
        + (16).to_bytes(4, "little")
        + (len(compressed) + 1).to_bytes(4, "little")
        + len(b"synthetic").to_bytes(4, "little")
        + compressed
    )

    with pytest.raises(RSSInventoryError, match="compressed length mismatch"):
        decompress_section(malformed, section_name="DATA FILES")


def test_operand_csv_lists_every_exact_source_operand_string(tmp_path) -> None:
    source = tmp_path / "synthetic.rss"
    source.write_bytes(b"source")
    inventory = build_inventory(
        source,
        SyntheticCompoundDocument(),
        include_private_text=True,
    )

    rows = list(csv.DictReader(io.StringIO(render_operand_inventory_csv(inventory))))

    assert [row["operand"] for row in rows] == ["#N7:1", "B3:0/0"]
    assert sum(int(row["occurrence_count"]) for row in rows) == 2
    assert sum(int(row["direct_occurrence_count"]) for row in rows) == 1
    assert sum(int(row["indirect_occurrence_count"]) for row in rows) == 1
    assert all(row["program_files"] == "2 MAIN" for row in rows)
    assert all(row["rung_locations"] == "2:0" for row in rows)


def test_operand_csv_redacts_operand_and_program_names_by_default(tmp_path) -> None:
    source = tmp_path / "synthetic.rss"
    source.write_bytes(b"source")
    inventory = build_inventory(source, SyntheticCompoundDocument())

    rows = list(csv.DictReader(io.StringIO(render_operand_inventory_csv(inventory))))

    assert all(row["operand"] == "" for row in rows)
    assert all(len(row["operand_sha256"]) == 64 for row in rows)
    assert all("MAIN" not in row["program_files"] for row in rows)
