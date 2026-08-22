"""Classify I/O applicability from explicit saved-configuration evidence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ApplicabilityStatus(StrEnum):
    """Evidence-bounded applicability of an I/O point."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    CONDITIONAL = "conditional"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class IOApplicabilityEvidence:
    """Explicit facts used to classify one I/O point.

    The model deliberately does not infer assignments from signal names or
    program references. A caller must state whether an assignment is known and
    whether any configuration-specific condition has been satisfied.
    """

    configured_asset_count: int | None
    minimum_asset_count: int | None = None
    declared_unused: bool = False
    assignment_known: bool = True
    condition_satisfied: bool | None = True


@dataclass(frozen=True)
class IOApplicability:
    """Applicability result with a concise evidence explanation."""

    status: ApplicabilityStatus
    reason: str


def classify_io_applicability(
    evidence: IOApplicabilityEvidence,
) -> IOApplicability:
    """Classify a point without treating code references as field use proof."""

    if evidence.declared_unused:
        return IOApplicability(
            ApplicabilityStatus.INACTIVE,
            "The source material explicitly declares this point unused.",
        )

    if (
        evidence.configured_asset_count is not None
        and evidence.minimum_asset_count is not None
        and evidence.configured_asset_count < evidence.minimum_asset_count
    ):
        return IOApplicability(
            ApplicabilityStatus.INACTIVE,
            "The saved asset count is below this point's minimum applicability.",
        )

    if evidence.condition_satisfied is False:
        return IOApplicability(
            ApplicabilityStatus.INACTIVE,
            "The saved configuration does not satisfy this point's condition.",
        )

    if not evidence.assignment_known:
        return IOApplicability(
            ApplicabilityStatus.UNRESOLVED,
            "The saved configuration does not identify this point's assignment.",
        )

    if evidence.condition_satisfied is None:
        return IOApplicability(
            ApplicabilityStatus.CONDITIONAL,
            "Applicability depends on a condition not resolved by current evidence.",
        )

    if evidence.configured_asset_count is None:
        return IOApplicability(
            ApplicabilityStatus.UNRESOLVED,
            "The configured asset count is unavailable.",
        )

    return IOApplicability(
        ApplicabilityStatus.ACTIVE,
        "The saved configuration satisfies all supplied applicability constraints.",
    )
