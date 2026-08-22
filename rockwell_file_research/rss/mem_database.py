"""Evidence-led decoding of rung-comment attachments in MEM DATABASE."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from rockwell_file_research.rss.compressed_section import decompress_section

_RUNG_KEY = re.compile(rb"\x11RUNG([0-9]{6})-([0-9]{6})")
_ADDRESS_KEY = re.compile(
    rb"(?P<length>[\x09\x0c])"
    rb"(?P<type>[A-Z])(?P<file>[0-9]{4}):(?P<element>[0-9]{3})"
    rb"(?:/(?P<bit>[0-9]{2}))?"
)


@dataclass(frozen=True)
class RungCommentRecord:
    """One length-delimited comment and its explicit file/rung attachment."""

    attachment_kind: str
    attachment_source: str
    attachment_key: str
    program_file_number: int | None
    rung_index: int | None
    address: str | None
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
    """Find the strict short or extended length field preceding a key."""

    comment_end = key_start - 1
    if comment_end < 1 or payload[comment_end] != 0:
        return None
    lower = max(3, comment_end - 65_539)
    candidates: list[tuple[int, bytes]] = []
    for length in range(1, min(254, comment_end - lower) + 1):
        text_start = comment_end - length
        if payload[text_start - 1] != length:
            continue
        if payload[text_start - 3 : text_start - 1] != b"\x00\x00":
            continue
        text = payload[text_start:comment_end]
        if _is_comment_text(text):
            candidates.append((text_start, text))
    marker = payload.rfind(b"\xff", lower, comment_end - 2)
    while marker >= lower:
        text_start = marker + 3
        length = int.from_bytes(payload[marker + 1 : text_start], "little")
        if (
            marker >= 2
            and payload[marker - 2 : marker] == b"\x00\x00"
            and text_start + length == comment_end
        ):
            text = payload[text_start:comment_end]
            if _is_comment_text(text):
                candidates.append((text_start, text))
        marker = payload.rfind(b"\xff", lower, marker)
    return candidates[-1] if candidates else None


def _canonical_address(match: re.Match[bytes]) -> str:
    """Normalize an observed fixed-width RSLogix address attachment key."""

    address = (
        f"{match.group('type').decode('ascii')}"
        f"{int(match.group('file'))}:{int(match.group('element'))}"
    )
    bit = match.group("bit")
    return f"{address}/{int(bit)}" if bit is not None else address


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
                attachment_kind="file_rung",
                attachment_source="rslogix_file_rung",
                attachment_key=match.group(0)[1:].decode("ascii"),
                program_file_number=int(match.group(1)),
                rung_index=int(match.group(2)),
                address=None,
                text_offset=text_offset,
                key_offset=match.start() + 1,
                length=len(encoded),
                sha256=hashlib.sha256(encoded).hexdigest(),
                text=decoded if include_private_text else None,
            )
        )
    for match in _ADDRESS_KEY.finditer(section.payload):
        if match.group("length")[0] != len(match.group(0)) - 1:
            continue
        comment = _comment_before_key(section.payload, match.start())
        if comment is None:
            continue
        text_offset, encoded = comment
        comments.append(
            RungCommentRecord(
                attachment_kind="address",
                attachment_source="rslogix_output_address",
                attachment_key=match.group(0)[1:].decode("ascii"),
                program_file_number=None,
                rung_index=None,
                address=_canonical_address(match),
                text_offset=text_offset,
                key_offset=match.start() + 1,
                length=len(encoded),
                sha256=hashlib.sha256(encoded).hexdigest(),
                text=encoded.decode("ascii") if include_private_text else None,
            )
        )
    comments.sort(
        key=lambda item: (
            item.attachment_kind,
            item.program_file_number if item.program_file_number is not None else -1,
            item.rung_index if item.rung_index is not None else -1,
            item.address or "",
        )
    )
    return MemDatabaseInspection(
        envelope_version=section.envelope_version,
        header_size=section.header_size,
        compressed_size=section.compressed_size,
        uncompressed_size=section.uncompressed_size,
        compressed_sha256=section.compressed_sha256,
        uncompressed_sha256=section.uncompressed_sha256,
        comments=comments,
    )
