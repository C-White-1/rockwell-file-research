"""Corroborate decoded binary words across redundant RSS sections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from rockwell_file_research.rss.models import (
    RSSBinaryDataFileEvidence,
    RSSDataFileSectionEvidence,
)

EXPECTED_SECTIONS = frozenset({"DATA FILES", "Extensional DATA FILES"})


@dataclass(frozen=True)
class CorroboratedBinaryDataFile:
    """Agreement result for one numbered binary data file."""

    file_number: int
    sections_consistent: bool
    element_count: int | None
    values_sha256: str | None
    words: tuple[int, ...] | None
    reason: str


def corroborate_binary_data_file(
    sections: Iterable[RSSDataFileSectionEvidence],
    file_number: int,
) -> CorroboratedBinaryDataFile:
    """Require one identical word array in each redundant data-file section."""

    found: dict[str, list[RSSBinaryDataFileEvidence]] = {}
    for section in sections:
        if section["name"] not in EXPECTED_SECTIONS or not section["present"]:
            continue
        found[section["name"]] = [
            array
            for array in section["binary_word_arrays"]
            if array["file_number"] == file_number
        ]

    if set(found) != EXPECTED_SECTIONS:
        return CorroboratedBinaryDataFile(
            file_number,
            False,
            None,
            None,
            None,
            "Both data-file sections are required.",
        )
    if any(len(matches) != 1 for matches in found.values()):
        return CorroboratedBinaryDataFile(
            file_number,
            False,
            None,
            None,
            None,
            "Each section must contain exactly one matching word array.",
        )

    standard = found["DATA FILES"][0]
    extensional = found["Extensional DATA FILES"][0]
    if (
        standard["element_count"] != extensional["element_count"]
        or standard["values_sha256"] != extensional["values_sha256"]
    ):
        return CorroboratedBinaryDataFile(
            file_number,
            False,
            None,
            None,
            None,
            "Element count or word-array digest differs between sections.",
        )

    standard_words = standard["words"]
    extensional_words = extensional["words"]
    words: tuple[int, ...] | None = None
    if standard_words is not None or extensional_words is not None:
        if standard_words is None or extensional_words is None:
            return CorroboratedBinaryDataFile(
                file_number,
                False,
                None,
                None,
                None,
                "Private words are present in only one section.",
            )
        words = tuple(standard_words)
        if words != tuple(extensional_words):
            return CorroboratedBinaryDataFile(
                file_number,
                False,
                None,
                None,
                None,
                "Private words differ between sections.",
            )

    return CorroboratedBinaryDataFile(
        file_number=file_number,
        sections_consistent=True,
        element_count=standard["element_count"],
        values_sha256=standard["values_sha256"],
        words=words,
        reason="Standard and extensional word arrays agree.",
    )
