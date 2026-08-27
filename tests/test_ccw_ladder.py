"""Tests for CCW Quick Ladder Diagram STF parsing."""

from rockwell_file_research.ccw.ladder import (
    LadderInstruction,
    LadderParallel,
    parse_stf,
)

SOURCE = """PROGRAM Sequence
#info= QLD
BOF
SOR [0,1] (**) (**) XIC [1,0] (*IN00*) (*Stop_PB*)
BST XIC [2,0] (*IN01*) (*Start_PB*) NXB XIC [2,1] (*OUT01*) (*Motor_01*) BND
XIO [3,0] (*OUT00*) (*Size_Fault*) OTE [4,0] (*OUT01*) (*Motor_01*) EOR [5,0]
SOR [0,4] (**) (**) XIC [1,0] (*IN02*) (*1PE*) OTS [4,0] (*OUT00*) (*Size_Fault*) EOR [5,0]
EOF
#end_info
END_PROGRAM
"""


def test_parse_stf_recovers_program_rungs_and_annotations() -> None:
    program = parse_stf(SOURCE)
    assert program.name == "Sequence"
    assert program.language == "QLD"
    assert len(program.rungs) == 2
    first = program.rungs[0].network.elements[0]
    assert isinstance(first, LadderInstruction)
    assert (first.mnemonic, first.operand, first.alias) == ("XIC", "IN00", "Stop_PB")
    assert first.position is not None
    assert (first.position.column, first.position.row) == (1, 0)
    assert program.diagnostics == ()


def test_parse_stf_builds_parallel_branch_topology() -> None:
    elements = parse_stf(SOURCE).rungs[0].network.elements
    branch = elements[1]
    assert isinstance(branch, LadderParallel)
    assert len(branch.branches) == 2
    assert [
        [item.operand for item in path.elements if isinstance(item, LadderInstruction)]
        for path in branch.branches
    ] == [["IN01"], ["OUT01"]]
    assert [
        item.mnemonic for item in elements if isinstance(item, LadderInstruction)
    ] == ["XIC", "XIO", "OTE"]
