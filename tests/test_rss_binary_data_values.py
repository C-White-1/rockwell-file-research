"""Controlled structural tests for RSS binary data-file words."""

from rockwell_file_research.rss.data_files import (
    DataFileRecord,
    scan_binary_data_file_words,
)


def _record(offset: int) -> DataFileRecord:
    return DataFileRecord(
        offset=offset,
        file_number=10,
        description="",
        name="BINARY",
        description_sha256="d" * 64,
        name_sha256="n" * 64,
        unknown_numeric_candidate=1,
        marker_offset=offset + 20,
    )


def test_decodes_unsigned_little_endian_binary_words():
    words = (0x00A5, 0x8112)
    value_bytes = b"".join(word.to_bytes(2, "little") for word in words)
    prefix = b"unrelated" + bytes.fromhex("03 80 03") + bytes(7)
    header = bytes.fromhex("02 00 01 00 00 00 FF FF")
    record_offset = len(prefix + header + value_bytes)

    decoded = scan_binary_data_file_words(
        prefix + header + value_bytes + b"catalogue",
        [_record(record_offset)],
    )

    assert len(decoded) == 1
    assert decoded[0].file_number == 10
    assert decoded[0].element_count == 2
    assert decoded[0].words == words
    assert len(decoded[0].values_sha256) == 64


def test_rejects_integer_type_marker_with_same_word_shape():
    values = bytes.fromhex("A5 00 12 81")
    prefix = b"unrelated" + bytes.fromhex("03 80 07") + bytes(7)
    header = bytes.fromhex("02 00 01 00 00 00 FF FF")
    record_offset = len(prefix + header + values)

    assert (
        scan_binary_data_file_words(
            prefix + header + values + b"catalogue",
            [_record(record_offset)],
        )
        == []
    )
