"""Controlled structural tests for RSS integer data-file values."""

from rockwell_file_research.rss.data_files import (
    DataFileRecord,
    scan_integer_data_file_values,
)


def _record(offset: int = 0) -> DataFileRecord:
    return DataFileRecord(
        offset=offset,
        file_number=11,
        description="CONFIG TEST",
        name="CONFIG",
        description_sha256="d" * 64,
        name_sha256="n" * 64,
        unknown_numeric_candidate=1,
        marker_offset=offset + 20,
    )


def test_decodes_signed_integer_values_with_offsets_and_digest():
    values = (101, -2, 32767, -32768)
    value_bytes = b"".join(value.to_bytes(2, "little", signed=True) for value in values)
    prefix = b"unrelated" + bytes.fromhex("03 80 07") + bytes(7)
    header = len(values).to_bytes(2, "little") + bytes.fromhex(
        "01 00 00 00 FF FF"
    )
    record_offset = len(prefix + header + value_bytes)
    payload = prefix + header + value_bytes + b"catalogue record"

    decoded = scan_integer_data_file_values(payload, [_record(record_offset)])

    assert len(decoded) == 1
    assert decoded[0].file_number == 11
    assert decoded[0].header_offset == len(prefix)
    assert decoded[0].values_offset == len(prefix) + 8
    assert decoded[0].element_count == 4
    assert decoded[0].values == values
    assert len(decoded[0].values_sha256) == 64


def test_rejects_same_shape_without_integer_type_marker():
    values = bytes.fromhex("65 00 CA 00")
    prefix = b"unrelated" + bytes.fromhex("03 80 08") + bytes(7)
    header = bytes.fromhex("02 00 01 00 00 00 FF FF")
    record_offset = len(prefix + header + values)

    assert scan_integer_data_file_values(
        prefix + header + values + b"catalogue",
        [_record(record_offset)],
    ) == []
