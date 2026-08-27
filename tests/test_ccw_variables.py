"""Tests for CCW global-variable evidence resolution."""

import zipfile
from pathlib import Path

from rockwell_file_research.ccw.variables import read_variable_catalogue


def test_catalogue_resolves_type_alias_and_physical_io(tmp_path: Path) -> None:
    source = tmp_path / "variables.ccwarc"
    prefix = "Controller/Controller/Micro850/Micro850/"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(
            prefix + "GlobalVariable.rtc", b"Global\0variables\0_IO_EM_DI_00\0IN00\0"
        )
        archive.writestr(
            prefix + "MICRO850_SymbolsTarget.xtc",
            b"TYPE\0BOOL\0_IO_EM_DI_00\0IN00\0END\0",
        )
        archive.writestr(prefix + "BUFFER_INPUTS.txt", "IN00 := _IO_EM_DI_00 ;\n")
        archive.writestr(
            prefix + "Sequence.stf",
            "PROGRAM Sequence\n#info= QLD\nBOF\nSOR [0,1] XIC [1,0] (*IN00*) (*Stop_PB*) EOR [2,0]\nEOF\n#end_info\nEND_PROGRAM\n",
        )
    catalogue = read_variable_catalogue(source)
    variables = {variable.name: variable for variable in catalogue.variables}
    assert variables["IN00"].kind == "user"
    assert variables["IN00"].data_type == "BOOL"
    assert variables["IN00"].aliases == ("Stop_PB",)
    assert variables["IN00"].physical_source == "_IO_EM_DI_00"
    assert variables["_IO_EM_DI_00"].kind == "physical_io"
    assert catalogue.diagnostics == ()


def test_catalogue_does_not_guess_ambiguous_types(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.ccwarc"
    prefix = "Controller/Controller/Micro850/Micro850/"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(prefix + "GlobalVariable.rtc", b"First\0Second\0")
        archive.writestr(
            prefix + "MICRO850_SymbolsTarget.xtc", b"BOOL\0DINT\0First\0Second\0"
        )
    catalogue = read_variable_catalogue(source)
    assert all(variable.data_type is None for variable in catalogue.variables)
    assert catalogue.diagnostics
