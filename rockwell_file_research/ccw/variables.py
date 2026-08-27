"""Conservative variable catalogue assembled from CCW archive evidence."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rockwell_file_research.ccw.ladder import (
    LadderInstruction,
    LadderParallel,
    LadderSeries,
    parse_stf,
)

VariableKind = Literal["user", "physical_io", "system", "register", "compiler"]


@dataclass(frozen=True)
class CCWVariable:
    """One global variable with provenance-preserving resolution evidence."""

    name: str
    scope: Literal["global"]
    kind: VariableKind
    data_type: str | None
    aliases: tuple[str, ...]
    physical_source: str | None
    physical_destination: str | None
    evidence_entries: tuple[str, ...]


@dataclass(frozen=True)
class CCWVariableCatalogue:
    """Resolved globals plus explicit diagnostics for uncertain evidence."""

    variables: tuple[CCWVariable, ...]
    diagnostics: tuple[str, ...]


_IDENTIFIER = re.compile(rb"[A-Za-z_][A-Za-z0-9_]{2,127}")
_ASSIGNMENT = re.compile(
    r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=\s*([A-Za-z_][A-Za-z0-9_]*)\s*;"
)
_IEC_TYPES = {
    "BOOL",
    "BYTE",
    "DINT",
    "DWORD",
    "INT",
    "LINT",
    "LREAL",
    "REAL",
    "SINT",
    "STRING",
    "TIME",
    "UDINT",
    "UINT",
    "ULINT",
    "USINT",
    "WORD",
}


def read_variable_catalogue(source: str | Path) -> CCWVariableCatalogue:
    """Resolve global variables without extracting private archive payloads."""

    with zipfile.ZipFile(source) as archive:
        global_entry = _one_entry(archive, "GlobalVariable.rtc")
        symbol_entry = _one_entry(archive, "_SymbolsTarget.xtc", suffix_match=True)
        declared = set(_identifiers(archive.read(global_entry)))
        symbol_tokens = _identifiers(archive.read(symbol_entry))
        symbol_names = set(symbol_tokens)
        candidates = declared & symbol_names
        data_types = sorted(_IEC_TYPES & symbol_names)
        proven_type = data_types[0] if len(data_types) == 1 else None
        diagnostics = (
            []
            if proven_type
            else [
                "global symbol table contains zero or multiple IEC types; individual types remain unresolved"
            ]
        )
        aliases = _aliases(archive)
        sources, destinations, mapping_entries = _io_mappings(archive)
        variables = tuple(
            CCWVariable(
                name=name,
                scope="global",
                kind=_kind(name),
                data_type=proven_type,
                aliases=tuple(sorted(aliases.get(name, set()))),
                physical_source=sources.get(name),
                physical_destination=destinations.get(name),
                evidence_entries=tuple(
                    sorted(
                        {global_entry, symbol_entry, *mapping_entries.get(name, set())}
                    )
                ),
            )
            for name in sorted(candidates)
            if _is_variable_name(name)
        )
    return CCWVariableCatalogue(variables, tuple(diagnostics))


def _one_entry(
    archive: zipfile.ZipFile, ending: str, *, suffix_match: bool = False
) -> str:
    folded = ending.casefold()
    matches = [
        name
        for name in archive.namelist()
        if (
            name.casefold().endswith(folded)
            if suffix_match
            else Path(name).name.casefold() == folded
        )
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {ending} entry; found {len(matches)}")
    return matches[0]


def _identifiers(payload: bytes) -> list[str]:
    return [match.group().decode("ascii") for match in _IDENTIFIER.finditer(payload)]


def _kind(name: str) -> VariableKind:
    if name.startswith(("__SYSVA_", "__PHY__")):
        return "system"
    if name.startswith("_IO_"):
        return "physical_io"
    if name.startswith("_REG_"):
        return "register"
    if name.startswith("__"):
        return "compiler"
    return "user"


def _is_variable_name(name: str) -> bool:
    return name not in _IEC_TYPES and name not in {"Global", "variables"}


def _io_mappings(
    archive: zipfile.ZipFile,
) -> tuple[dict[str, str], dict[str, str], dict[str, set[str]]]:
    sources: dict[str, str] = {}
    destinations: dict[str, str] = {}
    evidence: dict[str, set[str]] = {}
    for name in archive.namelist():
        if not name.lower().endswith(".txt"):
            continue
        text = archive.read(name).decode("utf-8-sig", errors="replace")
        for left, right in _ASSIGNMENT.findall(text):
            if right.startswith("_IO_") and not left.startswith("_IO_"):
                sources[left] = right
                evidence.setdefault(left, set()).add(name)
            if left.startswith("_IO_") and not right.startswith("_IO_"):
                destinations[right] = left
                evidence.setdefault(right, set()).add(name)
    return sources, destinations, evidence


def _aliases(archive: zipfile.ZipFile) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for name in archive.namelist():
        if not name.lower().endswith(".stf"):
            continue
        program = parse_stf(archive.read(name).decode("utf-8-sig", errors="replace"))
        for rung in program.rungs:
            for instruction in _instructions(rung.network):
                if instruction.operand and instruction.alias:
                    result.setdefault(instruction.operand, set()).add(instruction.alias)
    return result


def _instructions(series: LadderSeries) -> list[LadderInstruction]:
    result: list[LadderInstruction] = []
    for element in series.elements:
        if isinstance(element, LadderInstruction):
            result.append(element)
        elif isinstance(element, LadderParallel):
            for branch in element.branches:
                result.extend(_instructions(branch))
    return result
