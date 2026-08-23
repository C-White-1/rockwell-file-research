"""Link decoded configuration addresses to HMI and ladder usage evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from rockwell_file_research.integration.addresses import parse_data_table_address
from rockwell_file_research.integration.models import PLCHMICrossReference


@dataclass(frozen=True)
class ConfigurationAddressImpact:
    """Conservative cross-artifact usage evidence for one PLC address."""

    address: str
    binding_count: int
    hmi_tags: tuple[str, ...]
    consumer_reference_count: int
    ladder_occurrence_count: int
    ladder_rungs: tuple[str, ...]


def load_cross_reference(path: Path) -> PLCHMICrossReference:
    """Load a generated cross-reference document with minimal contract checks."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("bindings"), list):
        raise TypeError("cross-reference document must contain a bindings array")
    return cast(PLCHMICrossReference, document)


def configuration_address_impact(
    report: PLCHMICrossReference, address: str
) -> ConfigurationAddressImpact:
    """Find exact structured bindings without requiring private address text."""

    parsed = parse_data_table_address(address)
    if parsed is None:
        return ConfigurationAddressImpact(address, 0, (), 0, 0, ())
    matches = [
        binding
        for binding in report["bindings"]
        if binding["prefix"].upper() == parsed.prefix
        and binding["file_number"] == parsed.file_number
        and binding["element_number"] == parsed.element_number
        and binding["subelement_number"] == parsed.subelement_number
        and binding["bit_number"] == parsed.bit_number
        and (binding["member"] or "").upper() == (parsed.member or "").upper()
    ]
    tags = {
        binding["tag_name"]
        if binding["tag_name"] is not None
        else f"sha256:{binding['tag_name_sha256'][:12]}"
        for binding in matches
    }
    occurrences = [
        occurrence
        for binding in matches
        for occurrence in binding["ladder_occurrences"]
    ]
    rungs = {
        f"P{occurrence['program_file_number']}:rung[{occurrence['rung_index']}]"
        for occurrence in occurrences
        if occurrence["program_file_number"] is not None
        and occurrence["rung_index"] is not None
    }
    return ConfigurationAddressImpact(
        address=address,
        binding_count=len(matches),
        hmi_tags=tuple(sorted(tags)),
        consumer_reference_count=sum(len(binding["consumers"]) for binding in matches),
        ladder_occurrence_count=len(occurrences),
        ladder_rungs=tuple(sorted(rungs)),
    )
