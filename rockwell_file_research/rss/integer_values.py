"""Corroborate decoded integer arrays across redundant RSS sections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from rockwell_file_research.rss.models import (
    RSSDataFileSectionEvidence,
    RSSIntegerDataFileEvidence,
)

EXPECTED_SECTIONS = frozenset({"DATA FILES", "Extensional DATA FILES"})


@dataclass(frozen=True)
class CorroboratedIntegerDataFile:
    """Agreement result for one numbered integer data file."""

    file_number: int
    sections_consistent: bool
    element_count: int | None
    values_sha256: str | None
    values: tuple[int, ...] | None
    reason: str


def corroborate_integer_data_file(
    sections: Iterable[RSSDataFileSectionEvidence],
    file_number: int,
) -> CorroboratedIntegerDataFile:
    """Require one identical array in each standard and extensional section."""

    found: dict[str, list[RSSIntegerDataFileEvidence]] = {}
    for section in sections:
        if section["name"] not in EXPECTED_SECTIONS or not section["present"]:
            continue
        matches = [
            array
            for array in section["integer_value_arrays"]
            if array["file_number"] == file_number
        ]
        found[section["name"]] = matches

    if set(found) != EXPECTED_SECTIONS:
        return CorroboratedIntegerDataFile(
            file_number,
            False,
            None,
            None,
            None,
            "Both data-file sections are required.",
        )
    if any(len(matches) != 1 for matches in found.values()):
        return CorroboratedIntegerDataFile(
            file_number,
            False,
            None,
            None,
            None,
            "Each section must contain exactly one matching array.",
        )

    standard = found["DATA FILES"][0]
    extensional = found["Extensional DATA FILES"][0]
    if (
        standard["element_count"] != extensional["element_count"]
        or standard["values_sha256"] != extensional["values_sha256"]
    ):
        return CorroboratedIntegerDataFile(
            file_number,
            False,
            None,
            None,
            None,
            "Element count or value-array digest differs between sections.",
        )

    standard_values = standard["values"]
    extensional_values = extensional["values"]
    values: tuple[int, ...] | None = None
    if standard_values is not None or extensional_values is not None:
        if standard_values is None or extensional_values is None:
            return CorroboratedIntegerDataFile(
                file_number,
                False,
                None,
                None,
                None,
                "Private values are present in only one section.",
            )
        values = tuple(int(value) for value in standard_values)
        if values != tuple(int(value) for value in extensional_values):
            return CorroboratedIntegerDataFile(
                file_number,
                False,
                None,
                None,
                None,
                "Private values differ between sections.",
            )

    return CorroboratedIntegerDataFile(
        file_number=file_number,
        sections_consistent=True,
        element_count=int(standard["element_count"]),
        values_sha256=str(standard["values_sha256"]),
        values=values,
        reason="Standard and extensional arrays agree.",
    )
