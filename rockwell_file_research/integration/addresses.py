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
_SELECTOR = re.compile(
    r"^(?:(?::(?P<element>\d+)(?:/(?P<bit>\d+)|\.(?P<member>[A-Za-z]+))?)|/(?P<file_bit>\d+))$"
)


@dataclass(frozen=True)
class DataTableAddress:
    """Conservative structural interpretation of one data-table address."""

    raw: str
    prefix: str
    file_number: int
    selector: str
    element_number: int | None
    bit_number: int | None
    member: str | None


def _location(prefix: str, selector: str) -> tuple[int | None, int | None, str | None]:
    """Interpret supported element/member selectors without value decoding."""

    match = _SELECTOR.fullmatch(selector)
    if match is None:
        return None, None, None
    file_bit = match["file_bit"]
    if file_bit is not None:
        bit_index = int(file_bit)
        if prefix == "B":
            return bit_index // 16, bit_index % 16, None
        return None, bit_index, None
    element = int(match["element"])
    bit = int(match["bit"]) if match["bit"] is not None else None
    member = match["member"].upper() if match["member"] is not None else None
    return element, bit, member


def _address(
    *, raw: str, prefix: str, file_number: int, selector: str
) -> DataTableAddress:
    element, bit, member = _location(prefix, selector)
    return DataTableAddress(
        raw=raw,
        prefix=prefix,
        file_number=file_number,
        selector=selector,
        element_number=element,
        bit_number=bit,
        member=member,
    )


def parse_data_table_address(value: str) -> DataTableAddress | None:
    """Return the file identity in an address, or ``None`` if unsupported."""

    raw = value.strip()
    match = _EXPLICIT_FILE.fullmatch(raw)
    if match is not None:
        return _address(
            raw=raw,
            prefix=match["prefix"].upper(),
            file_number=int(match["file_number"]),
            selector=match["selector"],
        )
    match = _DEFAULT_FILE.fullmatch(raw)
    if match is None:
        return None
    prefix = match["prefix"].upper()
    return _address(
        raw=raw,
        prefix=prefix,
        file_number=_DEFAULT_FILE_NUMBERS[prefix],
        selector=match["selector"],
    )
