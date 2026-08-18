"""Evidence-led inspection of the RSS PROCESSOR section."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

ASCII_REGION = re.compile(rb"[\x20-\x7e]{4,}")


@dataclass(frozen=True)
class ProcessorTextRegion:
    """One printable processor-stream region and its byte provenance."""

    classification: str
    offset: int
    length: int
    sha256: str
    text: str | None


def _classify(payload: bytes) -> str:
    """Classify only patterns directly supported by observed delimiters."""

    if payload == b"CProc>":
        return "serialization_class"
    if b"%" in payload and len(payload) >= 32:
        return "processor_configuration_record"
    if b"!" in payload and b"\\" in payload:
        return "communication_route_candidate"
    return "project_identifier_candidate"


def inspect_processor_text(
    payload: bytes,
    *,
    include_private_text: bool = False,
) -> list[ProcessorTextRegion]:
    """Locate text regions while keeping decoded values private by default."""

    regions: list[ProcessorTextRegion] = []
    for match in ASCII_REGION.finditer(payload):
        region = match.group()
        regions.append(
            ProcessorTextRegion(
                classification=_classify(region),
                offset=match.start(),
                length=len(region),
                sha256=hashlib.sha256(region).hexdigest(),
                text=(
                    region.decode("ascii", errors="replace")
                    if include_private_text
                    else None
                ),
            )
        )
    return regions
