"""Tests for the normalized, schema-validated CCW project contract."""

import copy
import zipfile
from pathlib import Path

import pytest
from jsonschema import ValidationError

from rockwell_file_research.ccw.project_model import build_project_model
from rockwell_file_research.ccw.project_validation import validate_project_model


def _archive(tmp_path: Path) -> Path:
    source = tmp_path / "private-name.ccwarc"
    prefix = "Controller/Controller/Micro850/Micro850/"
    names = b"_IO_EM_DI_00\0Start\0Motor\0"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(
            "RevisionInfo.txt",
            "<RevisionInfo><CCWVersion>22</CCWVersion>"
            "<ProjectName>Controlled</ProjectName></RevisionInfo>",
        )
        archive.writestr(
            "Controller/Controller/persist.ccwx",
            b"target=2080-LC50-48QWB-SIM\0",
        )
        archive.writestr(prefix + "GlobalVariable.rtc", names)
        archive.writestr(prefix + "MICRO850_SymbolsTarget.xtc", b"BOOL\0" + names)
        archive.writestr(prefix + "BUFFER_INPUTS.txt", "Start := _IO_EM_DI_00 ;\n")
        archive.writestr(
            prefix + "Sequence.stf",
            "PROGRAM Sequence\n#info= QLD\nBOF\n"
            "SOR [0,1] BST XIC [1,0] (*Start*) NXB XIC [1,1] (*Motor*) "
            "BND OTE [2,0] (*Motor*) EOR [3,0]\n"
            "EOF\n#end_info\nEND_PROGRAM\n",
        )
    return source


def test_project_model_is_neutral_recursive_and_schema_valid(tmp_path: Path) -> None:
    model = build_project_model(_archive(tmp_path), source_label="controlled-fixture")

    validate_project_model(model)

    assert model["schema_version"] == "ccw-project-v1"
    assert model["source"]["reference"] == "controlled-fixture"
    assert model["project"]["name"] == "Controlled"
    assert model["controller"] == {
        "catalog_number": "2080-LC50-48QWB-SIM",
        "simulated": True,
    }
    network = model["programs"][0]["rungs"][0]["network"]
    assert network["elements"][0]["kind"] == "parallel"
    variables = {item["name"]: item for item in model["variables"]}
    assert variables["Start"]["physical_source"] == "_IO_EM_DI_00"
    assert variables["Motor"]["usages"][0]["branch_path"] == [1]
    assert model["unresolved_operands"] == []


def test_project_schema_rejects_an_unknown_contract_version(tmp_path: Path) -> None:
    model = copy.deepcopy(build_project_model(_archive(tmp_path)))
    model["schema_version"] = "future-contract"

    with pytest.raises(ValidationError):
        validate_project_model(model)
