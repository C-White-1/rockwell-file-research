"""Load external, evidence-backed meanings for decoded RSS values."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SemanticValueRule:
    """One documented interpretation of a raw value at an RSS address."""

    address: str
    semantic_name: str
    raw_value: int
    interpretation: str
    evidence: str


SemanticValueProfile = dict[tuple[str, int], SemanticValueRule]


def load_semantic_value_profile(path: Path) -> SemanticValueProfile:
    """Load a strict CSV profile without deriving undocumented meanings."""

    profile: SemanticValueProfile = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = {
            "address",
            "semantic_name",
            "raw_value",
            "interpretation",
            "evidence",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(
                "semantic profile requires address, semantic_name, raw_value, "
                "interpretation, and evidence columns"
            )
        for line_number, row in enumerate(reader, start=2):
            address = row["address"].strip().upper()
            semantic_name = row["semantic_name"].strip()
            interpretation = row["interpretation"].strip()
            evidence = row["evidence"].strip()
            if not all((address, semantic_name, interpretation, evidence)):
                raise ValueError(f"semantic profile row {line_number} is incomplete")
            try:
                raw_value = int(row["raw_value"], 0)
            except ValueError as error:
                raise ValueError(
                    f"semantic profile row {line_number} has an invalid raw_value"
                ) from error
            key = (address, raw_value)
            if key in profile:
                raise ValueError(
                    f"semantic profile contains duplicate rule for {address}={raw_value}"
                )
            profile[key] = SemanticValueRule(
                address, semantic_name, raw_value, interpretation, evidence
            )
    return profile
