"""Validated decompression of length-declared RSS section envelopes."""

from __future__ import annotations

import hashlib
import zlib
from dataclasses import dataclass

from rockwell_file_research.rss.errors import RSSInventoryError

ENVELOPE_SIZE = 16


@dataclass(frozen=True)
class CompressedSection:
    """Verified envelope metadata and decompressed RSS section evidence."""

    envelope_version: int
    header_size: int
    compressed_size: int
    uncompressed_size: int
    compressed_sha256: str
    uncompressed_sha256: str
    payload: bytes


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def decompress_section(payload: bytes, *, section_name: str) -> CompressedSection:
    """Validate and decompress one observed 16-byte RSS section envelope."""

    if len(payload) < ENVELOPE_SIZE:
        raise RSSInventoryError(f"{section_name} section envelope is truncated")
    envelope_version = int.from_bytes(payload[0:4], "little")
    header_size = int.from_bytes(payload[4:8], "little")
    declared_compressed_size = int.from_bytes(payload[8:12], "little")
    declared_uncompressed_size = int.from_bytes(payload[12:16], "little")
    if header_size != ENVELOPE_SIZE:
        raise RSSInventoryError(
            f"{section_name} section has unsupported header size {header_size}"
        )
    compressed = payload[header_size:]
    if declared_compressed_size != len(compressed):
        raise RSSInventoryError(
            f"{section_name} compressed length mismatch: declared "
            f"{declared_compressed_size}, found {len(compressed)}"
        )
    try:
        uncompressed = zlib.decompress(compressed)
    except zlib.error as error:
        raise RSSInventoryError(
            f"{section_name} section has invalid zlib data"
        ) from error
    if declared_uncompressed_size != len(uncompressed):
        raise RSSInventoryError(
            f"{section_name} uncompressed length mismatch: declared "
            f"{declared_uncompressed_size}, found {len(uncompressed)}"
        )
    return CompressedSection(
        envelope_version=envelope_version,
        header_size=header_size,
        compressed_size=len(compressed),
        uncompressed_size=len(uncompressed),
        compressed_sha256=_sha256(compressed),
        uncompressed_sha256=_sha256(uncompressed),
        payload=uncompressed,
    )
