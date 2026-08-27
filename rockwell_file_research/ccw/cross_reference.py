"""Cross-reference authored CCW ladder operands against resolved variables."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rockwell_file_research.ccw.ladder import (
    GridPosition,
    LadderInstruction,
    LadderParallel,
    LadderSeries,
    STFParseError,
    parse_stf,
)
from rockwell_file_research.ccw.variables import CCWVariable, read_variable_catalogue

AccessMode = Literal["read", "write", "unknown"]


@dataclass(frozen=True)
class CCWVariableUsage:
    """One authored instruction reference to a variable."""

    program: str
    rung: int
    branch_path: tuple[int, ...]
    parallel_depth: int
    mnemonic: str
    access: AccessMode
    position: GridPosition | None


@dataclass(frozen=True)
class CCWVariableCrossReference:
    """Resolved declaration, physical mapping and all ladder references."""

    variable: CCWVariable
    usages: tuple[CCWVariableUsage, ...]
    seal_in_rungs: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class CCWCrossReferenceReport:
    """Project-wide operand cross-reference with conservative diagnostics."""

    variables: tuple[CCWVariableCrossReference, ...]
    unresolved_operands: tuple[str, ...]
    diagnostics: tuple[str, ...]


_READ_MNEMONICS = {"XIC", "XIO"}
_WRITE_MNEMONICS = {"OTE", "OTS", "OTR"}


def build_cross_reference(source: str | Path) -> CCWCrossReferenceReport:
    """Build a project-wide cross-reference directly from a CCW archive."""

    catalogue = read_variable_catalogue(source)
    declarations = {variable.name: variable for variable in catalogue.variables}
    usages: dict[str, list[CCWVariableUsage]] = {}
    diagnostics = list(catalogue.diagnostics)
    with zipfile.ZipFile(source) as archive:
        for entry in sorted(
            name for name in archive.namelist() if name.lower().endswith(".stf")
        ):
            try:
                program = parse_stf(
                    archive.read(entry).decode("utf-8-sig", errors="replace")
                )
            except STFParseError as error:
                diagnostics.append(f"{entry}: {error}")
                continue
            diagnostics.extend(f"{entry}: {item}" for item in program.diagnostics)
            for rung_number, rung in enumerate(program.rungs, start=1):
                for instruction, branch_path, depth in _walk(rung.network):
                    if not instruction.operand:
                        continue
                    usages.setdefault(instruction.operand, []).append(
                        CCWVariableUsage(
                            program=program.name,
                            rung=rung_number,
                            branch_path=branch_path,
                            parallel_depth=depth,
                            mnemonic=instruction.mnemonic,
                            access=_access(instruction.mnemonic),
                            position=instruction.position,
                        )
                    )
    resolved = tuple(
        CCWVariableCrossReference(
            variable=variable,
            usages=tuple(usages.get(variable.name, [])),
            seal_in_rungs=_seal_in_rungs(usages.get(variable.name, [])),
        )
        for variable in catalogue.variables
    )
    unresolved = tuple(sorted(set(usages) - set(declarations)))
    return CCWCrossReferenceReport(resolved, unresolved, tuple(diagnostics))


def _walk(
    series: LadderSeries,
    path: tuple[int, ...] = (),
    depth: int = 0,
) -> list[tuple[LadderInstruction, tuple[int, ...], int]]:
    result: list[tuple[LadderInstruction, tuple[int, ...], int]] = []
    for element in series.elements:
        if isinstance(element, LadderInstruction):
            result.append((element, path, depth))
        elif isinstance(element, LadderParallel):
            for branch_index, branch in enumerate(element.branches):
                result.extend(_walk(branch, (*path, branch_index), depth + 1))
    return result


def _access(mnemonic: str) -> AccessMode:
    if mnemonic in _READ_MNEMONICS:
        return "read"
    if mnemonic in _WRITE_MNEMONICS:
        return "write"
    return "unknown"


def _seal_in_rungs(usages: list[CCWVariableUsage]) -> tuple[tuple[str, int], ...]:
    grouped: dict[tuple[str, int], list[CCWVariableUsage]] = {}
    for usage in usages:
        grouped.setdefault((usage.program, usage.rung), []).append(usage)
    return tuple(
        location
        for location, rung_usages in sorted(grouped.items())
        if any(item.mnemonic == "OTE" for item in rung_usages)
        and any(
            item.access == "read" and item.parallel_depth > 0 for item in rung_usages
        )
    )
