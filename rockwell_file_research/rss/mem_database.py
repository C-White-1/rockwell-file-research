"""Evidence-led decoding of rung-comment attachments in MEM DATABASE."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from rockwell_file_research.rss.compressed_section import decompress_section

_RUNG_KEY = re.compile(rb"\x11RUNG([0-9]{6})-([0-9]{6})")


@dataclass(frozen=True)
class RungCommentRecord:
    """One length-delimited comment and its explicit file/rung attachment."""

    program_file_number: int
    rung_index: int
    text_offset: int
    key_offset: int
    length: int
    sha256: str
    text: str | None


@dataclass(frozen=True)
class MemDatabaseInspection:
    """Verified MEM DATABASE compression and rung-comment evidence."""

    envelope_version: int
    header_size: int
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    comments: list[RungCommentRecord]


def _is_comment_text(payload: bytes) -> bool:
    """Accept observed printable text plus standard multiline whitespace."""

    return bool(payload) and all(
        byte in (9, 10, 13) or 32 <= byte <= 126 for byte in payload
    )


def _comment_before_key(payload: bytes, key_start: int) -> tuple[int, bytes] | None:
    """Find the strict one-byte-length field immediately preceding a key."""

    comment_end = key_start - 1
    if comment_end < 1 or payload[comment_end] != 0:
        return None
    lower = max(3, comment_end - 256)
    candidates: list[tuple[int, bytes]] = []
    for length_offset in range(lower, comment_end):
        length = payload[length_offset]
        text_start = length_offset + 1
        if text_start + length != comment_end:
            continue
        text = payload[text_start:comment_end]
        if payload[length_offset - 3 : length_offset] != b"\x00\x00\x00":
            continue
        if _is_comment_text(text):
            candidates.append((text_start, text))
    return candidates[-1] if candidates else None


def inspect_mem_database(
    payload: bytes,
    *,
    include_private_text: bool,
) -> MemDatabaseInspection:
    """Decode only repeatably proven rung-comment attachment records."""

    section = decompress_section(payload, section_name="MEM DATABASE")
    comments: list[RungCommentRecord] = []
    for match in _RUNG_KEY.finditer(section.payload):
        comment = _comment_before_key(section.payload, match.start())
        if comment is None:
            continue
        text_offset, encoded = comment
        decoded = encoded.decode("ascii")
        comments.append(
            RungCommentRecord(
                program_file_number=int(match.group(1)),
                rung_index=int(match.group(2)),
                text_offset=text_offset,
                key_offset=match.start() + 1,
                length=len(encoded),
                sha256=hashlib.sha256(encoded).hexdigest(),
                text=decoded if include_private_text else None,
            )
        )
    comments.sort(key=lambda item: (item.program_file_number, item.rung_index))
    return MemDatabaseInspection(
        envelope_version=section.envelope_version,
        header_size=section.header_size,
        compressed_size=section.compressed_size,
        uncompressed_size=section.uncompressed_size,
        compressed_sha256=section.compressed_sha256,
        uncompressed_sha256=section.uncompressed_sha256,
        comments=comments,
    )
