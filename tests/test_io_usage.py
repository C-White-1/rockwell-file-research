"""Tests for conservative drawing-to-RSS I/O usage correlation."""

from typing import cast

from rockwell_file_research.integration.io_usage import correlate_io_usage
from rockwell_file_research.rss.models import RSSInventory


def _inventory() -> RSSInventory:
    return cast(
        RSSInventory,
        {
            "program_files": {
                "rung_records": [
                    {
                        "program_file_number": 4,
                        "rung_index": 0,
                        "byte_length": 134,
                    },
                    {
                        "program_file_number": 4,
                        "rung_index": 34,
                        "byte_length": 5065,
                    },
                ],
                "operands": [
                    {
                        "operand": "I:0.1/0",
                        "program_file_number": 4,
                        "program_file_name": "IO MAPPING",
                        "rung_index": 0,
                        "indirect": False,
                    },
                    {
                        "operand": "I:0.1/0",
                        "program_file_number": 4,
                        "program_file_name": "IO MAPPING",
                        "rung_index": 34,
                        "indirect": False,
                    },
                ],
            }
        },
    )


def test_correlates_compact_and_canonical_io_spellings_without_data_loss():
    (usage,) = correlate_io_usage(
        ["I:0/16"], _inventory(), max_compact_rung_bytes=1024
    )

    assert usage.canonical_address == "I:0.1/0"
    assert usage.candidate_reference_count == 2
    assert usage.compact_reference_count == 1
    assert [reference.rung_byte_length for reference in usage.references] == [134, 5065]


def test_preserves_unsupported_and_unobserved_addresses():
    unsupported, unobserved = correlate_io_usage(
        ["not-an-address", "O:0/11"], _inventory()
    )

    assert unsupported.canonical_address is None
    assert unsupported.references == ()
    assert unobserved.canonical_address == "O:0.0/11"
    assert unobserved.candidate_reference_count == 0
    assert unobserved.compact_reference_count is None
