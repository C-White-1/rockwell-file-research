"""Tests for CCW ladder-variable cross-references."""

import zipfile
from pathlib import Path

from rockwell_file_research.ccw.cross_reference import build_cross_reference


def test_cross_reference_tracks_branches_writers_and_seal_in(tmp_path: Path) -> None:
    source = tmp_path / "cross-reference.ccwarc"
    prefix = "Controller/Controller/Micro850/Micro850/"
    names = b"_IO_EM_DO_01\0Start\0Motor\0"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(prefix + "GlobalVariable.rtc", names)
        archive.writestr(prefix + "MICRO850_SymbolsTarget.xtc", b"BOOL\0" + names)
        archive.writestr(prefix + "BUFFER_OUTPUTS.txt", "_IO_EM_DO_01 := Motor ;\n")
        archive.writestr(
            prefix + "Sequence.stf",
            "PROGRAM Sequence\n#info= QLD\nBOF\nSOR [0,1] XIC [1,0] (*Start*) BST XIC [2,0] (*Start*) NXB XIC [2,1] (*Motor*) BND OTE [3,0] (*Motor*) EOR [4,0]\nEOF\n#end_info\nEND_PROGRAM\n",
        )
    report = build_cross_reference(source)
    variables = {item.variable.name: item for item in report.variables}
    motor = variables["Motor"]
    assert [(usage.mnemonic, usage.access) for usage in motor.usages] == [
        ("XIC", "read"),
        ("OTE", "write"),
    ]
    assert motor.usages[0].branch_path == (1,)
    assert motor.seal_in_rungs == (("Sequence", 1),)
    assert motor.variable.physical_destination == "_IO_EM_DO_01"
    assert report.unresolved_operands == ()


def test_cross_reference_reports_undeclared_operands(tmp_path: Path) -> None:
    source = tmp_path / "unknown.ccwarc"
    prefix = "Controller/Controller/Micro850/Micro850/"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(prefix + "GlobalVariable.rtc", b"Known\0")
        archive.writestr(prefix + "MICRO850_SymbolsTarget.xtc", b"BOOL\0Known\0")
        archive.writestr(
            prefix + "Sequence.stf",
            "PROGRAM Sequence\n#info= QLD\nBOF\nSOR [0,1] XIC [1,0] (*Missing*) EOR [2,0]\nEOF\n#end_info\nEND_PROGRAM\n",
        )
    assert build_cross_reference(source).unresolved_operands == ("Missing",)
