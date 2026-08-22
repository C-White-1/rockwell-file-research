"""Correlate declared MicroLogix I/O addresses with RSS operand evidence."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import cast

from rockwell_file_research.integration.addresses import (
    canonicalize_micrologix_io_address,
)
from rockwell_file_research.rss.models import RSSInventory


@dataclass(frozen=True)
class IOUsageReference:
    """Location and framing evidence for one matching RSS operand."""

    program_file_number: int
    program_file_name: str | None
    rung_index: int
    rung_byte_length: int | None
    indirect: bool


@dataclass(frozen=True)
class IOUsage:
    """Conservative RSS evidence associated with one declared I/O address."""

    source_address: str
    canonical_address: str | None
    candidate_reference_count: int
    compact_reference_count: int | None
    references: tuple[IOUsageReference, ...]


def _rung_lengths(inventory: RSSInventory) -> dict[tuple[int, int], int]:
    program_files = cast(Mapping[str, object], inventory.get("program_files", {}))
    records = cast(
        Iterable[Mapping[str, object]], program_files.get("rung_records", [])
    )
    result: dict[tuple[int, int], int] = {}
    for record in records:
        file_number = record.get("program_file_number")
        rung_index = record.get("rung_index")
        byte_length = record.get("byte_length")
        if all(
            isinstance(value, int) for value in (file_number, rung_index, byte_length)
        ):
            result[(cast(int, file_number), cast(int, rung_index))] = cast(
                int, byte_length
            )
    return result


def correlate_io_usage(
    addresses: Iterable[str],
    inventory: RSSInventory,
    *,
    max_compact_rung_bytes: int | None = None,
) -> tuple[IOUsage, ...]:
    """Return all matching operand evidence for each supplied I/O address.

    ``max_compact_rung_bytes`` is an explicit analysis policy, not a format
    fact. When supplied, it counts references whose enclosing decoded rung is
    no larger than that limit. All references remain present in ``references``
    so larger or unresolved serialized regions are never discarded.
    """

    program_files = cast(Mapping[str, object], inventory.get("program_files", {}))
    operands = cast(Iterable[Mapping[str, object]], program_files.get("operands", []))
    rung_lengths = _rung_lengths(inventory)
    indexed: dict[str, list[IOUsageReference]] = {}
    for operand in operands:
        raw_operand = operand.get("operand")
        file_number = operand.get("program_file_number")
        rung_index = operand.get("rung_index")
        if not (
            isinstance(raw_operand, str)
            and isinstance(file_number, int)
            and isinstance(rung_index, int)
        ):
            continue
        canonical = canonicalize_micrologix_io_address(raw_operand.lstrip("#"))
        if canonical is None:
            continue
        name = operand.get("program_file_name")
        indexed.setdefault(canonical, []).append(
            IOUsageReference(
                program_file_number=file_number,
                program_file_name=name if isinstance(name, str) else None,
                rung_index=rung_index,
                rung_byte_length=rung_lengths.get((file_number, rung_index)),
                indirect=bool(operand.get("indirect", False)),
            )
        )

    result: list[IOUsage] = []
    for source_address in addresses:
        canonical = canonicalize_micrologix_io_address(source_address)
        references = tuple(indexed.get(canonical or "", []))
        compact_count = None
        if max_compact_rung_bytes is not None:
            compact_count = sum(
                reference.rung_byte_length is not None
                and reference.rung_byte_length <= max_compact_rung_bytes
                for reference in references
            )
        result.append(
            IOUsage(
                source_address=source_address,
                canonical_address=canonical,
                candidate_reference_count=len(references),
                compact_reference_count=compact_count,
                references=references,
            )
        )
    return tuple(result)
