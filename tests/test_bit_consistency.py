"""Tests for explicit configuration-to-bit consistency checks."""

from rockwell_file_research.integration.bit_consistency import (
    BitExpectation,
    compare_bit_expectations,
)


def test_reports_matching_and_differing_bits():
    results = compare_bit_expectations(
        [0b0010],
        [
            BitExpectation("set", 0, 1, True, "fixture"),
            BitExpectation("unexpected", 0, 0, True, "fixture"),
        ],
    )

    assert results[0].observed_state is True
    assert results[0].matches is True
    assert results[1].observed_state is False
    assert results[1].matches is False


def test_preserves_unresolved_out_of_range_expectation():
    (result,) = compare_bit_expectations(
        [0], [BitExpectation("missing", 2, 0, False, "fixture")]
    )

    assert result.observed_state is None
    assert result.matches is None
    assert "does not contain" in result.diagnostic


def test_rejects_invalid_bit_index_without_shifting():
    (result,) = compare_bit_expectations(
        [0], [BitExpectation("invalid", 0, 16, False, "fixture")]
    )

    assert result.observed_state is None
    assert result.matches is None
    assert "invalid" in result.diagnostic
