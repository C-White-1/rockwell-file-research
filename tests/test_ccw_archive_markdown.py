"""Tests for the privacy-aware CCW archive Markdown report."""

import zipfile
from pathlib import Path

from rockwell_file_research.ccw.archive import inspect_ccwarc
from rockwell_file_research.ccw.archive_markdown import render_ccw_archive_markdown
from rockwell_file_research.ccw.cross_reference import build_cross_reference


def test_markdown_report_uses_neutral_label_and_resolved_evidence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "private-name.ccwarc"
    prefix = "Controller/Controller/Micro850/Micro850/"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(
            "RevisionInfo.txt",
            "<RevisionInfo><CCWVersion>22</CCWVersion><ProjectName>Controlled</ProjectName></RevisionInfo>",
        )
        archive.writestr("Controller/Controller/persist.ccwx", b"2080-LC50-48QWB-SIM\0")
        archive.writestr(prefix + "GlobalVariable.rtc", b"_IO_EM_DI_00\0Start\0")
        archive.writestr(
            prefix + "MICRO850_SymbolsTarget.xtc", b"BOOL\0_IO_EM_DI_00\0Start\0"
        )
        archive.writestr(prefix + "BUFFER_INPUTS.txt", "Start := _IO_EM_DI_00 ;\n")
        archive.writestr(
            prefix + "Sequence.stf",
            "PROGRAM Sequence\n#info= QLD\nBOF\nSOR [0,1] XIC [1,0] (*Start*) (*Start_PB*) EOR [2,0]\nEOF\n#end_info\nEND_PROGRAM\n",
        )
    markdown = render_ccw_archive_markdown(
        inspect_ccwarc(source),
        build_cross_reference(source),
        source_label="controlled-fixture",
    )
    assert "`controlled-fixture`" in markdown
    assert "private-name.ccwarc" not in markdown
    assert "| Start | BOOL | Start_PB | _IO_EM_DI_00 |" in markdown
    assert "| Start | Sequence | 1 | - | XIC | read | 1,0 |" in markdown
