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
    r"^(?:(?::(?P<element>\d+)(?:\.(?P<subelement>\d+))?"
    r"(?:/(?:(?P<bit>\d+)|(?P<slash_member>[A-Za-z]+))|"
    r"\.(?P<member>[A-Za-z]+))?)|/(?P<file_bit>\d+))$"
)
_MICROLOGIX_IO_BIT = re.compile(
    r"^(?P<prefix>[IO]):(?P<slot>\d+)"
    r"(?:\.(?P<word>\d+))?/(?P<bit>\d+)$",
    re.IGNORECASE,
)
_MICROLOGIX_IO_WORD = re.compile(
    r"^(?P<prefix>[IO]):(?P<slot>\d+)\.(?P<word>\d+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DataTableAddress:
    """Conservative structural interpretation of one data-table address."""

    raw: str
    prefix: str
    file_number: int
    selector: str
    element_number: int | None
    subelement_number: int | None
    bit_number: int | None
    member: str | None


def _location(
    prefix: str, selector: str
) -> tuple[int | None, int | None, int | None, str | None]:
    """Interpret supported element/member selectors without value decoding."""

    match = _SELECTOR.fullmatch(selector)
    if match is None:
        return None, None, None, None
    file_bit = match["file_bit"]
    if file_bit is not None:
        bit_index = int(file_bit)
        if prefix == "B":
            return bit_index // 16, None, bit_index % 16, None
        return None, None, bit_index, None
    element = int(match["element"])
    subelement = int(match["subelement"]) if match["subelement"] is not None else None
    bit = int(match["bit"]) if match["bit"] is not None else None
    member_text = match["member"] or match["slash_member"]
    member = member_text.upper() if member_text is not None else None
    return element, subelement, bit, member


def _address(
    *, raw: str, prefix: str, file_number: int, selector: str
) -> DataTableAddress:
    element, subelement, bit, member = _location(prefix, selector)
    return DataTableAddress(
        raw=raw,
        prefix=prefix,
        file_number=file_number,
        selector=selector,
        element_number=element,
        subelement_number=subelement,
        bit_number=bit,
        member=member,
    )


def canonical_address_key(
    address: DataTableAddress,
) -> tuple[str, int, int | None, int | None, int | None, str | None]:
    """Return a comparable location key for equivalent address spellings."""

    subelement = address.subelement_number
    if address.prefix in {"I", "O"} and address.element_number is not None:
        subelement = subelement or 0
    return (
        address.prefix,
        address.file_number,
        address.element_number,
        subelement,
        address.bit_number,
        address.member,
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


def canonicalize_micrologix_io_address(value: str) -> str | None:
    """Return canonical slot/word I/O notation for a MicroLogix address.

    Drawings and operator-facing material may flatten an embedded I/O image,
    for example ``I:0/16``. RSS evidence represents the same location with an
    explicit 16-bit word selector: ``I:0.1/0``. This function performs only
    that structural normalization. It does not infer a signal's purpose,
    physical terminal, module placement, or whether an address is used.

    Word-oriented expansion-module addresses such as ``I:1.0`` are already
    canonical and are preserved. Unsupported text returns ``None``.
    """

    raw = value.strip()
    bit_match = _MICROLOGIX_IO_BIT.fullmatch(raw)
    if bit_match is not None:
        prefix = bit_match["prefix"].upper()
        slot = int(bit_match["slot"])
        explicit_word = bit_match["word"]
        bit = int(bit_match["bit"])
        if explicit_word is None:
            word, bit = divmod(bit, 16)
        else:
            word = int(explicit_word)
            if bit > 15:
                return None
        return f"{prefix}:{slot}.{word}/{bit}"

    word_match = _MICROLOGIX_IO_WORD.fullmatch(raw)
    if word_match is None:
        return None
    return (
        f"{word_match['prefix'].upper()}:"
        f"{int(word_match['slot'])}.{int(word_match['word'])}"
    )
