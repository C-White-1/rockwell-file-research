"""Tests for privacy-aware comparisons of corroborated RSS data values."""

import csv
import io
from pathlib import Path
from typing import cast

from rockwell_file_research.rss.models import RSSInventory
from rockwell_file_research.rss.value_comparison import (
    compare_data_values,
    render_data_value_comparison_csv,
    render_data_value_comparison_markdown,
)
from rockwell_file_research.rss.value_semantics import load_semantic_value_profile


def _inventory(*, integer: list[int] | None, words: list[int] | None) -> RSSInventory:
    integer_hash = "i-same" if integer in (None, [1, 2]) else "i-different"
    binary_hash = "b-same" if words in (None, [0x00A5]) else "b-different"
    sections = []
    for name in ("DATA FILES", "Extensional DATA FILES"):
        sections.append(
            {
                "name": name,
                "present": True,
                "private_values_included": integer is not None or words is not None,
                "integer_value_arrays": [
                    {
                        "file_number": 11,
                        "element_count": 2,
                        "values_sha256": integer_hash,
                        "values": integer,
                    }
                ],
                "binary_word_arrays": [
                    {
                        "file_number": 10,
                        "element_count": 1,
                        "values_sha256": binary_hash,
                        "words": words,
                    }
                ],
            }
        )
    return cast(RSSInventory, {"data_file_sections": sections})


def test_private_comparison_reports_exact_equal_and_changed_values() -> None:
    rows = compare_data_values(
        _inventory(integer=[1, 2], words=[0x00A5]),
        _inventory(integer=[1, 3], words=[0x00A5]),
    )
    indexed = {row.address: row for row in rows}

    assert indexed["N11:0"].status == "equal"
    assert indexed["N11:1"].status == "changed"
    assert indexed["N11:1"].left_value == 2
    assert indexed["N11:1"].right_value == 3
    assert indexed["B10:0"].status == "equal"


def test_redacted_comparison_uses_digest_without_exposing_values() -> None:
    rows = compare_data_values(
        _inventory(integer=None, words=None),
        _inventory(integer=None, words=None),
    )

    assert {row.status for row in rows} == {"equal_by_array_digest"}
    rendered = list(csv.DictReader(io.StringIO(render_data_value_comparison_csv(rows))))
    assert all(row["left_decimal_value"] == "" for row in rendered)
    assert all(row["right_decimal_value"] == "" for row in rendered)


def test_redacted_different_digest_does_not_claim_element_change() -> None:
    left = _inventory(integer=None, words=None)
    right = _inventory(integer=None, words=None)
    for section in right["data_file_sections"]:
        section["integer_value_arrays"][0]["values_sha256"] = "different"

    indexed = {row.address: row for row in compare_data_values(left, right)}

    assert indexed["N11:0"].status == "redacted_difference"
    assert indexed["N11:1"].status == "redacted_difference"


def test_missing_file_is_distinct_from_inconsistent_existing_evidence() -> None:
    left = _inventory(integer=[1, 2], words=[0x00A5])
    right = _inventory(integer=[1, 2], words=[0x00A5])
    for section in left["data_file_sections"]:
        section["binary_word_arrays"] = []

    indexed = {row.address: row for row in compare_data_values(left, right)}

    assert indexed["B10:0"].status == "missing_left"


def test_variant_profiles_translate_raw_changes_without_hard_coding_meaning(
    tmp_path: Path,
) -> None:
    left_profile_path = tmp_path / "left.csv"
    right_profile_path = tmp_path / "right.csv"
    header = "address,semantic_name,raw_value,interpretation,evidence\n"
    left_profile_path.write_text(
        header + "N11:1,pump_count,2,Two pumps,HMI enum\n", encoding="utf-8"
    )
    right_profile_path.write_text(
        header + "N11:1,pump_count,3,Three pumps,HMI enum\n", encoding="utf-8"
    )
    comparisons = compare_data_values(
        _inventory(integer=[1, 2], words=[0x00A5]),
        _inventory(integer=[1, 3], words=[0x00A5]),
    )

    rows = list(
        csv.DictReader(
            io.StringIO(
                render_data_value_comparison_csv(
                    comparisons,
                    left_profile=load_semantic_value_profile(left_profile_path),
                    right_profile=load_semantic_value_profile(right_profile_path),
                )
            )
        )
    )
    indexed = {row["address"]: row for row in rows}

    assert indexed["N11:1"]["semantic_name"] == "pump_count"
    assert indexed["N11:1"]["semantic_status"] == "semantic_changed"
    assert indexed["N11:1"]["left_interpretation"] == "Two pumps"
    assert indexed["N11:1"]["right_interpretation"] == "Three pumps"


def test_variant_specific_meaning_can_change_when_raw_value_is_equal(
    tmp_path: Path,
) -> None:
    left_profile_path = tmp_path / "left.csv"
    right_profile_path = tmp_path / "right.csv"
    header = "address,semantic_name,raw_value,interpretation,evidence\n"
    left_profile_path.write_text(
        header + "N11:1,drive_type,2,PF4-series VFD,Left manual\n",
        encoding="utf-8",
    )
    right_profile_path.write_text(
        header + "N11:1,drive_type,2,PF525 VFD,Right manual\n",
        encoding="utf-8",
    )
    comparisons = compare_data_values(
        _inventory(integer=[1, 2], words=[0x00A5]),
        _inventory(integer=[1, 2], words=[0x00A5]),
    )
    rows = list(
        csv.DictReader(
            io.StringIO(
                render_data_value_comparison_csv(
                    comparisons,
                    left_profile=load_semantic_value_profile(left_profile_path),
                    right_profile=load_semantic_value_profile(right_profile_path),
                    semantic_only=True,
                )
            )
        )
    )

    assert len(rows) == 1
    assert rows[0]["status"] == "equal"
    assert rows[0]["semantic_status"] == "semantic_changed"
    assert rows[0]["left_interpretation"] == "PF4-series VFD"
    assert rows[0]["right_interpretation"] == "PF525 VFD"


def test_semantic_profile_rejects_duplicate_address_value_rules(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "duplicate.csv"
    profile.write_text(
        "address,semantic_name,raw_value,interpretation,evidence\n"
        "N11:0,mode,1,Fill,HMI enum\n"
        "N11:0,mode,1,Fill again,HMI enum\n",
        encoding="utf-8",
    )

    try:
        load_semantic_value_profile(profile)
    except ValueError as error:
        assert "duplicate rule" in str(error)
    else:
        raise AssertionError("duplicate semantic rule was accepted")


def test_markdown_report_summarizes_raw_and_semantic_changes(tmp_path: Path) -> None:
    left_path = tmp_path / "left.csv"
    right_path = tmp_path / "right.csv"
    header = "address,semantic_name,raw_value,interpretation,evidence\n"
    left_path.write_text(
        header + "N11:1,drive_type,2,PF4-series VFD,Left manual\n",
        encoding="utf-8",
    )
    right_path.write_text(
        header + "N11:1,drive_type,2,PF525 VFD,Right manual\n",
        encoding="utf-8",
    )

    report = render_data_value_comparison_markdown(
        compare_data_values(
            _inventory(integer=[1, 2], words=[0x00A5]),
            _inventory(integer=[1, 2], words=[0x00A5]),
        ),
        left_profile=load_semantic_value_profile(left_path),
        right_profile=load_semantic_value_profile(right_path),
        semantic_only=True,
    )

    assert "| Reported addresses | 1 |" in report
    assert "| Raw value changes | 0 |" in report
    assert "| Semantic changes | 1 |" in report
    assert "PF4-series VFD" in report
    assert "PF525 VFD" in report
    assert "not a live controller observation" in report
