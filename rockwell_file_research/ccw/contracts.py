"""Declarative semantic contracts for supported CCW report sections."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionContract:
    """Expected tables and settings within one semantic report section."""

    title: str
    table_headers: tuple[frozenset[str], ...] = ()
    setting_labels: frozenset[str] = frozenset()
    required: bool = True


TAG_HEADERS = frozenset({"Name", "Data Type", "Address", "Controller", "Access"})
SCREEN_LIST_HEADERS = frozenset({"Name", "Number", "Description", "Rights"})
SCREEN_OBJECT_HEADERS = frozenset({"Object Name", "Tag", "Position", "Size"})
ALARM_HEADERS = frozenset({"Trigger", "Alarm Type", "Message"})
CONTROLLER_HEADERS = frozenset({"Name", "Controller Type", "Address"})
COMMUNICATION_SETTINGS = frozenset({"Protocol :", "Connection Type :"})

SECTION_CONTRACTS = (
    SectionContract("TAG REPORT", (TAG_HEADERS,)),
    SectionContract(
        "SCREEN REPORT",
        (SCREEN_LIST_HEADERS, SCREEN_OBJECT_HEADERS),
    ),
    SectionContract(
        "COMMUNICATION REPORT",
        (CONTROLLER_HEADERS,),
        COMMUNICATION_SETTINGS,
    ),
    SectionContract("ALARM REPORT", (ALARM_HEADERS,), required=False),
)
