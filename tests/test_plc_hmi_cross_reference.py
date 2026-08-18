"""Tests for conservative PLC–HMI address correlation."""

from typing import cast

from rockwell_file_research.ccw.models import CCWReport
from rockwell_file_research.integration.addresses import parse_data_table_address
from rockwell_file_research.integration.cross_reference import (
    build_plc_hmi_cross_reference,
)
from rockwell_file_research.rss.models import RSSInventory


def _hmi() -> CCWReport:
    return cast(
        CCWReport,
        {
            "source": {"path": "hmi-001", "size": 10, "sha256": "h" * 64},
            "tags": [
                {"name": "Start", "address": "B9/3"},
                {"name": "Output", "address": "O:0/1"},
                {"name": "Missing", "address": "N99:0"},
                {"name": "Opaque", "address": "not-an-address"},
            ],
        },
    )


def _plc() -> RSSInventory:
    return cast(
        RSSInventory,
        {
            "source": {"reference": "plc-001", "size": 20, "sha256": "p" * 64},
            "data_file_catalogue": {
                "record_count": 2,
                "records": [
                    {"file_number": 0, "name": "OUTPUT", "name_sha256": "o" * 64},
                    {
                        "file_number": 9,
                        "name": "HMI Commands",
                        "name_sha256": "b" * 64,
                    },
                ],
            },
        },
    )


def test_address_parser_handles_explicit_and_default_file_numbers() -> None:
    explicit = parse_data_table_address("t4:1.dn")
    physical = parse_data_table_address("o:0/1")

    assert explicit is not None
    assert (explicit.prefix, explicit.file_number, explicit.selector) == (
        "T",
        4,
        ":1.dn",
    )
    assert physical is not None
    assert (physical.prefix, physical.file_number) == ("O", 0)
    assert parse_data_table_address("not-an-address") is None


def test_cross_reference_redacts_private_text_and_preserves_uncertainty() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc())

    assert result["summary"] == {
        "hmi_tag_count": 4,
        "address_count": 4,
        "resolved_count": 2,
        "unresolved_count": 1,
        "unsupported_count": 1,
        "rss_catalogue_record_count": 2,
    }
    assert [binding["status"] for binding in result["bindings"]] == [
        "resolved",
        "resolved",
        "unresolved",
        "unsupported",
    ]
    assert all(binding["tag_name"] is None for binding in result["bindings"])
    assert all(binding["address"] is None for binding in result["bindings"])
    assert result["file_usage"][0]["rss_record_name"] is None


def test_cross_reference_private_opt_in_exposes_join_evidence() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc(), include_private_text=True)

    assert result["bindings"][0]["tag_name"] == "Start"
    assert result["bindings"][0]["address"] == "B9/3"
    assert result["bindings"][0]["rss_record_name"] == "HMI Commands"
    assert result["file_usage"][1]["rss_record_name"] == "HMI Commands"
