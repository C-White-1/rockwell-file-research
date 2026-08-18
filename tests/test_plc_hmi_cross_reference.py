"""Tests for conservative PLC–HMI address correlation."""

from typing import cast

from rockwell_file_research.ccw.models import CCWReport
from rockwell_file_research.integration.addresses import parse_data_table_address
from rockwell_file_research.integration.cross_reference import (
    build_plc_hmi_cross_reference,
)
from rockwell_file_research.integration.export import _omit_sha256_fields
from rockwell_file_research.integration.markdown import render_cross_reference_markdown
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
            "screen_objects": [
                {
                    "screen": "Main",
                    "name": "Start button",
                    "tag_1": "Write Tag",
                    "tag_2": "start",
                    "tag_3": "-",
                    "source_row": "12",
                }
            ],
            "alarms": [
                {"trigger": "Start", "message": "Start alarm", "source_row": "8"}
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
                    {
                        "file_number": 0,
                        "name": "OUTPUT",
                        "name_sha256": "o" * 64,
                        "unknown_numeric_candidate": 8,
                    },
                    {
                        "file_number": 9,
                        "name": "HMI Commands",
                        "name_sha256": "b" * 64,
                        "unknown_numeric_candidate": 2,
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
    assert (physical.prefix, physical.file_number, physical.element_number) == (
        "O",
        0,
        0,
    )
    assert parse_data_table_address("not-an-address") is None


def test_binary_file_level_bit_resolves_to_word_and_bit() -> None:
    address = parse_data_table_address("B9/20")

    assert address is not None
    assert (address.element_number, address.bit_number) == (1, 4)


def test_cross_reference_redacts_private_text_and_preserves_uncertainty() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc())

    assert result["summary"] == {
        "hmi_tag_count": 4,
        "address_count": 4,
        "resolved_count": 2,
        "unresolved_count": 1,
        "unsupported_count": 1,
        "rss_catalogue_record_count": 2,
        "address_elements_exceeding_rss_numeric_candidate": 0,
        "consumer_reference_count": 2,
        "screen_object_reference_count": 1,
        "alarm_reference_count": 1,
        "tags_with_consumers": 1,
        "tags_without_consumers": 3,
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
    assert result["bindings"][0]["exceeds_rss_numeric_candidate"] is False
    assert result["file_usage"][1]["highest_element_number"] == 0


def test_cross_reference_private_opt_in_exposes_join_evidence() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc(), include_private_text=True)

    assert result["bindings"][0]["tag_name"] == "Start"
    assert result["bindings"][0]["address"] == "B9/3"
    assert result["bindings"][0]["rss_record_name"] == "HMI Commands"
    assert result["bindings"][0]["consumers"] == [
        {
            "kind": "screen_object",
            "field": "tag_2",
            "source_row": "12",
            "screen_sha256": result["bindings"][0]["consumers"][0]["screen_sha256"],
            "label_sha256": result["bindings"][0]["consumers"][0]["label_sha256"],
            "screen": "Main",
            "label": "Start button",
        },
        {
            "kind": "alarm",
            "field": "trigger",
            "source_row": "8",
            "screen_sha256": None,
            "label_sha256": result["bindings"][0]["consumers"][1]["label_sha256"],
            "screen": None,
            "label": "Start alarm",
        },
    ]
    assert result["file_usage"][1]["rss_record_name"] == "HMI Commands"


def test_readable_copy_can_omit_all_sha256_fields() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc(), include_private_text=True)

    readable = _omit_sha256_fields(result)

    assert "sha256" not in str(readable)
    assert "HMI Commands" in str(readable)


def test_markdown_report_shows_clear_binding_and_consumers() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc(), include_private_text=True)

    markdown = render_cross_reference_markdown(result)

    assert markdown.startswith("<!-- markdownlint-disable MD013 -->")
    assert "# PLC–HMI Cross-reference" in markdown
    assert "| Start | B9/3 | 9 | element 0, bit 3 | HMI Commands |" in markdown
    assert "screen Main: Start button; alarm: Start alarm" in markdown
    assert "## Evidence limitations" in markdown
