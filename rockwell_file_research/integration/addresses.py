"""Parse RSLogix 500 data-table addresses without interpreting their values."""

from __future__ import annotations

import re
from dataclasses import dataclass

_EXPLICIT_FILE = re.compile(
    r"^(?P<prefix>[A-Za-z]+)(?P<file_number>\d+)(?P<selector>[:/.].+)$"
)
_DEFAULT_FILE = re.compile(
    r"^(?P<prefix>[OISBTCRNF])(?P<selector>[:/.].+)$",
    re.IGNORECASE,
)
_DEFAULT_FILE_NUMBERS = {
    "O": 0,
    "I": 1,
    "S": 2,
    "B": 3,
    "T": 4,
    "C": 5,
    "R": 6,
    "N": 7,
    "F": 8,
}


@dataclass(frozen=True)
class DataTableAddress:
    """Conservative structural interpretation of one data-table address."""

    raw: str
    prefix: str
    file_number: int
    selector: str


def parse_data_table_address(value: str) -> DataTableAddress | None:
    """Return the file identity in an address, or ``None`` if unsupported."""

    raw = value.strip()
    match = _EXPLICIT_FILE.fullmatch(raw)
    if match is not None:
        return DataTableAddress(
            raw=raw,
            prefix=match["prefix"].upper(),
            file_number=int(match["file_number"]),
            selector=match["selector"],
        )
    match = _DEFAULT_FILE.fullmatch(raw)
    if match is None:
        return None
    prefix = match["prefix"].upper()
    return DataTableAddress(
        raw=raw,
        prefix=prefix,
        file_number=_DEFAULT_FILE_NUMBERS[prefix],
        selector=match["selector"],
    )
