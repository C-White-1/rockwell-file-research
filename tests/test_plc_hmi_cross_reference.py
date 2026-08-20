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
            "program_files": {
                "operands": [
                    {
                        "offset": 100,
                        "sha256": "1" * 64,
                        "indirect": False,
                        "operand": "B9:0/3",
                        "program_file_number": 0,
                        "program_file_name_sha256": "m" * 64,
                        "program_file_name": "MAIN",
                        "rung_index": 0,
                        "rung_start_offset": 80,
                        "rung_end_offset": 180,
                    },
                    {
                        "offset": 200,
                        "sha256": "2" * 64,
                        "indirect": True,
                        "operand": "#B9:0/3",
                        "program_file_number": 0,
                        "program_file_name_sha256": "m" * 64,
                        "program_file_name": "MAIN",
                        "rung_index": 1,
                        "rung_start_offset": 180,
                        "rung_end_offset": 280,
                    },
                    {
                        "offset": 300,
                        "sha256": "3" * 64,
                        "indirect": False,
                        "operand": "N7:1",
                        "program_file_number": 3,
                        "program_file_name_sha256": "a" * 64,
                        "program_file_name": "APP SETUP",
                        "rung_index": 2,
                        "rung_start_offset": 280,
                        "rung_end_offset": 380,
                    },
                ]
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

    extended_physical = parse_data_table_address("I:0.1/3")
    assert extended_physical is not None
    assert (
        extended_physical.element_number,
        extended_physical.subelement_number,
        extended_physical.bit_number,
    ) == (0, 1, 3)


def test_binary_file_level_bit_resolves_to_word_and_bit() -> None:
    address = parse_data_table_address("B9/20")

    assert address is not None
    assert (address.element_number, address.bit_number) == (1, 4)


def test_timer_member_slash_and_dot_forms_are_equivalent() -> None:
    dotted = parse_data_table_address("T4:1.DN")
    slashed = parse_data_table_address("T4:1/DN")

    assert dotted is not None
    assert slashed is not None
    assert dotted.member == slashed.member == "DN"


def test_cross_reference_redacts_private_text_and_preserves_uncertainty() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc())

    assert result["schema_version"] == (
        "rockwell-file-research.plc-hmi-cross-reference.v4"
    )
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
        "ladder_operand_occurrence_count": 2,
        "ladder_program_file_count": 1,
        "distinct_ladder_rung_count": 2,
        "rung_scoped_ladder_operand_occurrence_count": 2,
        "direct_ladder_operand_occurrence_count": 1,
        "indirect_ladder_operand_occurrence_count": 1,
        "bindings_with_ladder_evidence": 1,
        "bindings_without_ladder_evidence": 3,
        "contained_bit_occurrence_count": 0,
        "bindings_with_contained_bit_evidence": 0,
        "contained_bit_program_file_count": 0,
        "distinct_contained_bit_rung_count": 0,
        "rung_scoped_contained_bit_occurrence_count": 0,
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
    assert result["file_usage"][1]["distinct_ladder_rung_count"] == 2
    assert [
        occurrence["operand"]
        for occurrence in result["bindings"][0]["ladder_occurrences"]
    ] == [None, None]
    assert result["bindings"][0]["contained_bit_occurrences"] == []
    assert result["contained_bit_rung_usage"] == []
    assert len(result["rung_usage"]) == 2
    assert result["rung_usage"][0]["program_file_number"] == 0
    assert result["rung_usage"][0]["rung_index"] == 0
    assert result["rung_usage"][0]["binding_count"] == 1
    assert result["rung_usage"][0]["operand_occurrence_count"] == 1
    assert result["rung_usage"][0]["tag_names"] == []


def test_cross_reference_private_opt_in_exposes_join_evidence() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc(), include_private_text=True)

    assert result["bindings"][0]["tag_name"] == "Start"
    assert result["bindings"][0]["address"] == "B9/3"
    assert result["bindings"][0]["rss_record_name"] == "HMI Commands"
    assert [
        occurrence["operand"]
        for occurrence in result["bindings"][0]["ladder_occurrences"]
    ] == ["B9:0/3", "#B9:0/3"]
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
    assert result["rung_usage"][0]["tag_names"] == ["Start"]


def test_readable_copy_can_omit_all_sha256_fields() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc(), include_private_text=True)

    readable = _omit_sha256_fields(result)

    assert "sha256" not in str(readable)
    assert "HMI Commands" in str(readable)


def test_whole_word_binding_keeps_contained_bits_separate_from_exact_matches() -> None:
    hmi = _hmi()
    hmi["tags"][0]["address"] = "B9:0"

    result = build_plc_hmi_cross_reference(hmi, _plc(), include_private_text=True)

    binding = result["bindings"][0]
    assert binding["ladder_occurrences"] == []
    assert [item["operand"] for item in binding["contained_bit_occurrences"]] == [
        "B9:0/3",
        "#B9:0/3",
    ]
    assert result["summary"]["distinct_contained_bit_rung_count"] == 2
    assert len(result["contained_bit_rung_usage"]) == 2
    assert result["contained_bit_rung_usage"][0]["tag_names"] == ["Start"]


def test_markdown_report_shows_clear_binding_and_consumers() -> None:
    result = build_plc_hmi_cross_reference(_hmi(), _plc(), include_private_text=True)

    markdown = render_cross_reference_markdown(result)

    assert markdown.startswith("<!-- markdownlint-disable MD013 -->")
    assert "# PLC–HMI Cross-reference" in markdown
    assert (
        "| Start | B9/3 | 9 | element 0, bit 3 | HMI Commands | 2 | "
        "0 MAIN rungs 0, 1 | 0 |" in markdown
    )
    assert "screen Main: Start button; alarm: Start alarm" in markdown
    assert "## Referenced rung index" in markdown
    assert "## Contained-bit rung index" in markdown
    assert "| 0 MAIN | 0 | 80–180 | 1 | 1 | 1 | 0 | 2 | Start |" in markdown
    assert "## Evidence limitations" in markdown
