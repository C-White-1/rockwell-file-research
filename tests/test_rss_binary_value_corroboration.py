"""Tests for redundant RSS binary-word corroboration."""

from copy import deepcopy
from typing import cast

from rockwell_file_research.rss.binary_values import corroborate_binary_data_file
from rockwell_file_research.rss.models import RSSDataFileSectionEvidence


def _section(name: str, *, digest: str = "a" * 64) -> RSSDataFileSectionEvidence:
    return cast(
        RSSDataFileSectionEvidence,
        {
            "name": name,
            "present": True,
            "binary_word_arrays": [
                {
                    "file_number": 10,
                    "element_count": 2,
                    "values_sha256": digest,
                    "words": [0x00A5, 0x8112],
                }
            ],
        },
    )


def test_corroborates_identical_standard_and_extensional_words():
    result = corroborate_binary_data_file(
        [_section("DATA FILES"), _section("Extensional DATA FILES")], 10
    )

    assert result.sections_consistent is True
    assert result.element_count == 2
    assert result.words == (0x00A5, 0x8112)
    assert result.values_sha256 == "a" * 64


def test_rejects_digest_disagreement_without_selecting_a_winner():
    standard = _section("DATA FILES")
    extensional = deepcopy(_section("Extensional DATA FILES"))
    extensional["binary_word_arrays"][0]["values_sha256"] = "b" * 64

    result = corroborate_binary_data_file([standard, extensional], 10)

    assert result.sections_consistent is False
    assert result.words is None
    assert "differs" in result.reason


def test_requires_both_redundant_sections():
    result = corroborate_binary_data_file([_section("DATA FILES")], 10)

    assert result.sections_consistent is False
    assert result.words is None
    assert "Both" in result.reason
