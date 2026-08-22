"""Compare explicit Boolean expectations with decoded 16-bit word arrays."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BitExpectation:
    """Expected state and evidence for one bit in a word array."""

    name: str
    word_index: int
    bit_index: int
    expected_state: bool
    evidence: str


@dataclass(frozen=True)
class BitConsistency:
    """Observed state and comparison result for one expectation."""

    expectation: BitExpectation
    observed_state: bool | None
    matches: bool | None
    diagnostic: str


def compare_bit_expectations(
    words: Sequence[int],
    expectations: Iterable[BitExpectation],
) -> tuple[BitConsistency, ...]:
    """Compare expectations without inventing values outside the word array."""

    results: list[BitConsistency] = []
    for expectation in expectations:
        if expectation.word_index < 0 or expectation.bit_index not in range(16):
            results.append(
                BitConsistency(
                    expectation,
                    None,
                    None,
                    "Expectation contains an invalid word or bit index.",
                )
            )
            continue
        if expectation.word_index >= len(words):
            results.append(
                BitConsistency(
                    expectation,
                    None,
                    None,
                    "Decoded word array does not contain the expected bit.",
                )
            )
            continue
        observed = bool(words[expectation.word_index] & (1 << expectation.bit_index))
        matches = observed is expectation.expected_state
        results.append(
            BitConsistency(
                expectation,
                observed,
                matches,
                "Observed bit matches expectation."
                if matches
                else "Observed bit differs from expectation.",
            )
        )
    return tuple(results)
