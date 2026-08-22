"""Synthetic tests for strict MEM DATABASE rung-comment decoding."""

import zlib

from rockwell_file_research.rss.mem_database import inspect_mem_database


def _envelope(payload: bytes) -> bytes:
    compressed = zlib.compress(payload)
    return (
        (2).to_bytes(4, "little")
        + (16).to_bytes(4, "little")
        + len(compressed).to_bytes(4, "little")
        + len(payload).to_bytes(4, "little")
        + compressed
    )


def _record(file_number: int, rung_index: int, text: bytes) -> bytes:
    key = f"RUNG{file_number:06d}-{rung_index:06d}".encode("ascii")
    return b"\x01\x00\x04\x00\x00\x00" + bytes([len(text)]) + text + b"\x00\x11" + key


def test_comments_are_sorted_and_multiline_text_is_preserved() -> None:
    payload = _record(3, 0, b"File three") + _record(2, 1, b"Line one\r\nLine two")

    inspected = inspect_mem_database(_envelope(payload), include_private_text=True)

    assert [
        (item.program_file_number, item.rung_index, item.text)
        for item in inspected.comments
    ] == [(2, 1, "Line one\r\nLine two"), (3, 0, "File three")]


def test_private_text_is_redacted_but_integrity_evidence_remains() -> None:
    inspected = inspect_mem_database(
        _envelope(_record(2, 0, b"Private comment")),
        include_private_text=False,
    )

    comment = inspected.comments[0]
    assert comment.text is None
    assert comment.length == len(b"Private comment")
    assert len(comment.sha256) == 64


def test_unframed_rung_like_text_is_not_promoted() -> None:
    inspected = inspect_mem_database(
        _envelope(b"printable\x00\x11RUNG000002-000000"),
        include_private_text=True,
    )

    assert inspected.comments == []
