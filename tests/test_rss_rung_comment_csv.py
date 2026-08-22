"""Tests for the engineer-facing RSS rung-comment CSV report."""

import csv
import io
from typing import cast

from rockwell_file_research.rss.models import RSSInventory
from rockwell_file_research.rss.rung_comment_csv import render_rung_comment_csv


def _inventory(*, include_text: bool) -> RSSInventory:
    return cast(
        RSSInventory,
        {
            "rung_comments": {
                "records": [
                    {
                        "attachment_kind": "file_rung",
                        "attachment_source": "rslogix_file_rung",
                        "attachment_key": "RUNG000002-000000",
                        "program_file_number": 2,
                        "rung_index": 0,
                        "address": None,
                        "text_offset": 100,
                        "key_offset": 120,
                        "length": 18,
                        "sha256": "a" * 64,
                        "text": "Line one\r\nLine two" if include_text else None,
                        "program_rung_corroborated": True,
                    },
                    {
                        "attachment_kind": "address",
                        "attachment_source": "rslogix_output_address",
                        "attachment_key": "B0003:000/01",
                        "program_file_number": 3,
                        "rung_index": 1,
                        "address": "B3:0/1",
                        "text_offset": 200,
                        "key_offset": 220,
                        "length": 5,
                        "sha256": "b" * 64,
                        "text": "Stale" if include_text else None,
                        "program_rung_corroborated": False,
                    },
                ]
            }
        },
    )


def test_report_distinguishes_corroborated_and_stale_attachments() -> None:
    rows = list(
        csv.DictReader(
            io.StringIO(render_rung_comment_csv(_inventory(include_text=True)))
        )
    )

    assert [row["attachment_status"] for row in rows] == [
        "corroborated",
        "address_attached",
    ]
    assert rows[1]["address"] == "B3:0/1"
    assert rows[0]["comment"] == "Line one\r\nLine two"


def test_report_is_redacted_when_inventory_text_is_redacted() -> None:
    rows = list(
        csv.DictReader(
            io.StringIO(render_rung_comment_csv(_inventory(include_text=False)))
        )
    )

    assert [row["comment"] for row in rows] == ["", ""]
    assert [row["comment_sha256"] for row in rows] == ["a" * 64, "b" * 64]
