"""Integrity checks for the controlled RSS instruction coverage ledger."""

from __future__ import annotations

import re
from pathlib import Path


def _coverage_text() -> str:
    return (Path(__file__).parents[1] / "RSS_INSTRUCTION_COVERAGE.md").read_text(
        encoding="utf-8"
    )


def test_confirmed_total_and_selectors_are_consistent() -> None:
    text = _coverage_text()
    rows = re.findall(
        r"^\| `([^`]+)` \| `0x([0-9A-F]+)` \|.*\| Confirmed \|$",
        text,
        flags=re.MULTILINE,
    )
    declared = re.search(r"^Confirmed total: \*\*(\d+)\*\*\.$", text, re.MULTILINE)

    assert declared is not None
    assert len(rows) == int(declared.group(1))
    assert len({mnemonic for mnemonic, _ in rows}) == len(rows)
    assert len({selector for _, selector in rows}) == len(rows)


def test_candidate_backlog_is_explicitly_empty() -> None:
    text = _coverage_text()

    assert "No unresolved mnemonic candidates remain" in text
