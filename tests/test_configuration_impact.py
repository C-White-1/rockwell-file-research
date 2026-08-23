"""Tests for semantic-setting links to HMI and ladder evidence."""

from pathlib import Path
from typing import cast

import pytest

from rockwell_file_research.integration.configuration_impact import (
    configuration_address_impact,
    load_cross_reference,
)
from rockwell_file_research.integration.models import PLCHMICrossReference


def _report(*, private_text: bool) -> PLCHMICrossReference:
    return cast(
        PLCHMICrossReference,
        {
            "bindings": [
                {
                    "prefix": "N",
                    "file_number": 11,
                    "element_number": 2,
                    "subelement_number": None,
                    "bit_number": None,
                    "member": None,
                    "tag_name": "PrimaryMeasurement" if private_text else None,
                    "tag_name_sha256": "a" * 64,
                    "consumers": [{"kind": "screen_object"}],
                    "ladder_occurrences": [
                        {
                            "program_file_number": 3,
                            "rung_index": 7,
                        }
                    ],
                }
            ]
        },
    )


def test_impact_matches_structured_address_and_preserves_rung_scope() -> None:
    impact = configuration_address_impact(_report(private_text=True), "N11:2")

    assert impact.binding_count == 1
    assert impact.hmi_tags == ("PrimaryMeasurement",)
    assert impact.consumer_reference_count == 1
    assert impact.ladder_occurrence_count == 1
    assert impact.ladder_rungs == ("P3:rung[7]",)


def test_redacted_impact_uses_a_bounded_tag_digest() -> None:
    impact = configuration_address_impact(_report(private_text=False), "N11:2")

    assert impact.hmi_tags == ("sha256:aaaaaaaaaaaa",)


def test_cross_reference_loader_rejects_missing_bindings(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text("{}", encoding="utf-8")

    with pytest.raises(TypeError, match="bindings array"):
        load_cross_reference(source)
