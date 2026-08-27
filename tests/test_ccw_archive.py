"""Tests for privacy-aware CCW archive inventorying."""

import zipfile
from pathlib import Path

from rockwell_file_research.ccw.archive import inspect_ccwarc


def test_inventory_discovers_metadata_programs_and_sensitive_entries(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "controlled.ccwarc"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "RevisionInfo.txt",
            "<RevisionInfo><CCWVersion>22</CCWVersion><ProjectName>Controlled</ProjectName></RevisionInfo>",
        )
        archive.writestr(
            "Controller/Controller/persist.ccwx", b"target=2080-LC50-48QWB-SIM\0"
        )
        prefix = "Controller/Controller/Micro850/Micro850/"
        archive.writestr(prefix + "Sequence.stf", "PROGRAM Sequence\n")
        archive.writestr(prefix + "SEQUENCE.txt", "lowered evidence\n")
        archive.writestr("Controller/Controller/DevicePref.xml", "<private />")
    inventory = inspect_ccwarc(archive_path)
    assert inventory.ccw_version == "22"
    assert inventory.project_name == "Controlled"
    assert inventory.controller_catalog == "2080-LC50-48QWB-SIM"
    assert inventory.simulator_target is True
    assert [program.name for program in inventory.programs] == ["SEQUENCE"]
    assert inventory.programs[0].has_ladder_source is True
    assert inventory.programs[0].has_lowered_text is True
    assert inventory.sensitive_entries == ("Controller/Controller/DevicePref.xml",)


def test_inventory_preserves_unknown_entry_names(tmp_path: Path) -> None:
    archive_path = tmp_path / "unknown.ccwarc"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("RevisionInfo.txt", "<RevisionInfo />")
        archive.writestr("Controller/evidence.opaque", b"unknown")
    assert inspect_ccwarc(archive_path).unknown_entries == (
        "Controller/evidence.opaque",
    )
