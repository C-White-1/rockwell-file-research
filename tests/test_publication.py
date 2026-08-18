"""Tests for the Git publication-policy boundary."""

from pathlib import Path

from rockwell_file_research.publication import (
    check_repository,
    prohibited_paths,
)


def test_private_roots_and_industrial_artifacts_are_rejected() -> None:
    paths = [
        "private-fixtures/controller/example.rss",
        "private-outputs/report.json",
        "PV800_PumpControl_V2.1/application.ccwsln",
        "public/vendor-example.ACD",
        "reports/generated.XLSX",
    ]

    assert prohibited_paths(paths) == sorted(paths)


def test_normal_source_documentation_and_schemas_are_allowed() -> None:
    paths = [
        "README.md",
        "rockwell_file_research/ccw/schema.py",
        "rockwell_file_research/ccw/schemas/ccw-report-v1.schema.json",
        "tests/fixtures/README.md",
        "tests/synthetic_expected.csv",
    ]

    assert prohibited_paths(paths) == []


def test_current_repository_tracks_no_prohibited_artifacts() -> None:
    repository = Path(__file__).parents[1]

    assert check_repository(repository) == []
