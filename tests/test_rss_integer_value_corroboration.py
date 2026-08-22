"""Tests for redundant RSS integer-array corroboration."""

from copy import deepcopy
from typing import cast

from rockwell_file_research.rss.integer_values import (
    corroborate_integer_data_file,
)
from rockwell_file_research.rss.models import RSSDataFileSectionEvidence


def _section(name: str, *, digest: str = "a" * 64) -> RSSDataFileSectionEvidence:
    return cast(
        RSSDataFileSectionEvidence,
        {
            "name": name,
            "present": True,
            "integer_value_arrays": [
                {
                    "file_number": 11,
                    "element_count": 3,
                    "values_sha256": digest,
                    "values": [1, 2, 3],
                }
            ],
        },
    )


def test_corroborates_identical_standard_and_extensional_arrays():
    result = corroborate_integer_data_file(
        [_section("DATA FILES"), _section("Extensional DATA FILES")], 11
    )

    assert result.sections_consistent is True
    assert result.element_count == 3
    assert result.values == (1, 2, 3)
    assert result.values_sha256 == "a" * 64


def test_rejects_digest_disagreement_without_selecting_a_winner():
    standard = _section("DATA FILES")
    extensional = deepcopy(_section("Extensional DATA FILES"))
    extensional["integer_value_arrays"][0]["values_sha256"] = "b" * 64

    result = corroborate_integer_data_file([standard, extensional], 11)

    assert result.sections_consistent is False
    assert result.values is None
    assert "differs" in result.reason


def test_requires_both_redundant_sections():
    result = corroborate_integer_data_file([_section("DATA FILES")], 11)

    assert result.sections_consistent is False
    assert result.values is None
    assert "Both" in result.reason
