"""Tests for evidence-preserving MicroLogix I/O address normalization."""

import pytest

from rockwell_file_research.integration.addresses import (
    canonicalize_micrologix_io_address,
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("I:0/0", "I:0.0/0"),
        ("I:0/15", "I:0.0/15"),
        ("I:0/16", "I:0.1/0"),
        ("I:0/19", "I:0.1/3"),
        ("O:0/1", "O:0.0/1"),
        ("o:0.0/9", "O:0.0/9"),
        ("I:1.0", "I:1.0"),
        ("O:1.1", "O:1.1"),
    ],
)
def test_canonicalizes_supported_io_notation(source: str, expected: str):
    assert canonicalize_micrologix_io_address(source) == expected


@pytest.mark.parametrize(
    "source",
    ["", "B3:0/1", "I:0.0/16", "I:slot/0", "not-an-address"],
)
def test_rejects_unsupported_or_invalid_io_notation(source: str):
    assert canonicalize_micrologix_io_address(source) is None
