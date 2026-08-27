"""Parser for CCW Quick Ladder Diagram (QLD) STF source."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path


class STFParseError(ValueError):
    """Raised when authored STF ladder structure is malformed."""


@dataclass(frozen=True)
class GridPosition:
    """Editor grid coordinate attached to a ladder element."""

    column: int
    row: int


@dataclass(frozen=True)
class LadderInstruction:
    """One authored ladder instruction."""

    mnemonic: str
    position: GridPosition | None
    operand: str | None
    alias: str | None
    annotations: tuple[str, ...]


@dataclass(frozen=True)
class LadderSeries:
    """Elements executed from left to right."""

    elements: tuple[LadderInstruction | LadderParallel, ...]


@dataclass(frozen=True)
class LadderParallel:
    """Two or more alternative ladder paths."""

    branches: tuple[LadderSeries, ...]


@dataclass(frozen=True)
class LadderRung:
    """One source rung with preserved evidence and parsed topology."""

    position: GridPosition | None
    network: LadderSeries
    raw: str


@dataclass(frozen=True)
class LadderProgram:
    """Authored QLD program recovered from STF source."""

    name: str
    language: str | None
    rungs: tuple[LadderRung, ...]
    diagnostics: tuple[str, ...]


_TOKEN = re.compile(
    r"\(\*.*?\*\)|\[\s*\d+\s*,\s*\d+\s*\]|[A-Za-z_][A-Za-z0-9_]*|\S", re.DOTALL
)
_POSITION = re.compile(r"\[\s*(\d+)\s*,\s*(\d+)\s*\]")
_COMMENT = re.compile(r"\(\*(.*?)\*\)", re.DOTALL)
_CONTROLS = {"BST", "NXB", "BND"}
_BOUNDARIES = {"SOR", "EOR"}
_METADATA = {"BOF", "EOF", "END_PROGRAM"}


def parse_stf(text: str) -> LadderProgram:
    """Parse CCW QLD STF while retaining unsupported tokens as diagnostics."""

    program_match = re.search(r"(?m)^PROGRAM\s+([A-Za-z_][A-Za-z0-9_]*)", text)
    if not program_match:
        raise STFParseError("STF source does not declare a PROGRAM")
    info_match = re.search(r"(?m)^#info=\s*([^\r\n]+)", text)
    body_match = re.search(r"(?ms)^BOF\s*$\s*(.*?)^EOF\s*$", text)
    if not body_match:
        raise STFParseError("STF source does not contain BOF/EOF boundaries")
    tokens = _TOKEN.findall(body_match.group(1))
    cursor = _Cursor(tokens)
    rungs: list[LadderRung] = []
    diagnostics: list[str] = []
    while cursor.current is not None:
        token = cursor.current.upper()
        if token == "SOR":
            rungs.append(_parse_rung(cursor))
        elif token in _METADATA or token.startswith("#") or _is_comment(cursor.current):
            cursor.advance()
        else:
            diagnostics.append(f"unscoped token preserved: {cursor.current}")
            cursor.advance()
    return LadderProgram(
        name=program_match.group(1),
        language=info_match.group(1).strip() if info_match else None,
        rungs=tuple(rungs),
        diagnostics=tuple(diagnostics),
    )


def read_stf_program(source: str | Path, program_name: str) -> LadderProgram:
    """Read and parse one STF program directly from a CCW archive."""

    with zipfile.ZipFile(source) as archive:
        matches = [
            name
            for name in archive.namelist()
            if Path(name).name.casefold() == f"{program_name}.stf".casefold()
        ]
        if len(matches) != 1:
            raise STFParseError(
                f"expected one STF source for {program_name!r}; found {len(matches)}"
            )
        return parse_stf(archive.read(matches[0]).decode("utf-8-sig"))


class _Cursor:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> str | None:
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def advance(self) -> str:
        if self.current is None:
            raise STFParseError("unexpected end of STF source")
        token = self.current
        self.index += 1
        return token


def _parse_rung(cursor: _Cursor) -> LadderRung:
    cursor.advance()  # SOR
    position = _take_position(cursor)
    while cursor.current is not None and _is_comment(cursor.current):
        cursor.advance()
    start = cursor.index
    network = _parse_series(cursor, {"EOR"})
    if cursor.current is None or cursor.current.upper() != "EOR":
        raise STFParseError("rung is missing EOR")
    cursor.advance()
    _take_position(cursor)
    return LadderRung(
        position=position,
        network=network,
        raw=" ".join(cursor.tokens[start : cursor.index]),
    )


def _parse_series(cursor: _Cursor, stops: set[str]) -> LadderSeries:
    elements: list[LadderInstruction | LadderParallel] = []
    while cursor.current is not None and cursor.current.upper() not in stops:
        token = cursor.current.upper()
        if token == "BST":
            cursor.advance()
            branches = [_parse_series(cursor, {"NXB", "BND"})]
            while cursor.current is not None and cursor.current.upper() == "NXB":
                cursor.advance()
                branches.append(_parse_series(cursor, {"NXB", "BND"}))
            if cursor.current is None or cursor.current.upper() != "BND":
                raise STFParseError("parallel branch is missing BND")
            cursor.advance()
            elements.append(LadderParallel(tuple(branches)))
        elif token in _CONTROLS | _BOUNDARIES:
            raise STFParseError(f"unexpected ladder control token: {token}")
        elif _is_comment(cursor.current):
            cursor.advance()
        else:
            elements.append(_parse_instruction(cursor))
    return LadderSeries(tuple(elements))


def _parse_instruction(cursor: _Cursor) -> LadderInstruction:
    mnemonic = cursor.advance().upper()
    position = _take_position(cursor)
    annotations: list[str] = []
    while cursor.current is not None and _is_comment(cursor.current):
        match = _COMMENT.fullmatch(cursor.advance())
        assert match is not None
        annotations.append(match.group(1).strip())
    return LadderInstruction(
        mnemonic=mnemonic,
        position=position,
        operand=annotations[0] if annotations else None,
        alias=annotations[1] if len(annotations) > 1 else None,
        annotations=tuple(annotations),
    )


def _take_position(cursor: _Cursor) -> GridPosition | None:
    if cursor.current is None:
        return None
    match = _POSITION.fullmatch(cursor.current)
    if not match:
        return None
    cursor.advance()
    return GridPosition(int(match.group(1)), int(match.group(2)))


def _is_comment(token: str) -> bool:
    return _COMMENT.fullmatch(token) is not None
