"""Tests for evidence-bounded I/O applicability classification."""

import pytest

from rockwell_file_research.integration.io_applicability import (
    ApplicabilityStatus,
    IOApplicabilityEvidence,
    classify_io_applicability,
)


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        (
            IOApplicabilityEvidence(2, declared_unused=True),
            ApplicabilityStatus.INACTIVE,
        ),
        (
            IOApplicabilityEvidence(2, minimum_asset_count=3),
            ApplicabilityStatus.INACTIVE,
        ),
        (
            IOApplicabilityEvidence(2, assignment_known=False),
            ApplicabilityStatus.UNRESOLVED,
        ),
        (
            IOApplicabilityEvidence(2, condition_satisfied=False),
            ApplicabilityStatus.INACTIVE,
        ),
        (
            IOApplicabilityEvidence(2, condition_satisfied=None),
            ApplicabilityStatus.CONDITIONAL,
        ),
        (IOApplicabilityEvidence(None), ApplicabilityStatus.UNRESOLVED),
        (IOApplicabilityEvidence(2, minimum_asset_count=2), ApplicabilityStatus.ACTIVE),
    ],
)
def test_classifies_only_from_explicit_evidence(evidence, expected):
    result = classify_io_applicability(evidence)

    assert result.status is expected
    assert result.reason


def test_declared_unused_takes_precedence_over_unknown_assignment():
    result = classify_io_applicability(
        IOApplicabilityEvidence(
            configured_asset_count=None,
            declared_unused=True,
            assignment_known=False,
            condition_satisfied=None,
        )
    )

    assert result.status is ApplicabilityStatus.INACTIVE


def test_excluded_condition_takes_precedence_over_unknown_assignment():
    result = classify_io_applicability(
        IOApplicabilityEvidence(
            configured_asset_count=2,
            assignment_known=False,
            condition_satisfied=False,
        )
    )

    assert result.status is ApplicabilityStatus.INACTIVE
