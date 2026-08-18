"""Typed, JSON-compatible models for normalized CCW report evidence."""

from typing import TypedDict

from rockwell_file_research.ccw.types import Workbook


class SourceEvidence(TypedDict):
    """Identity and integrity evidence for the source workbook."""

    path: str
    size: int
    sha256: str


class ApplicationIdentity(TypedDict):
    """Reported PanelView application identity."""

    name: str
    target: str
    version: str


class TagRecord(TypedDict):
    """One normalized external-tag record."""

    name: str
    data_type: str
    address: str
    controller: str
    description: str
    entry_min: str
    entry_max: str
    access: str
    update_rate_ms: str
    scaling_enabled: str
    raw_min: str
    raw_max: str
    scaled_min: str
    scaled_max: str
    source_row: str


class ScreenRecord(TypedDict):
    """One screen-list entry."""

    name: str
    number: str
    description: str
    rights: str
    source_row: str


class ScreenObjectRecord(TypedDict):
    """One visualization object and its reported tag evidence."""

    screen: str
    name: str
    tag_1: str
    tag_2: str
    tag_3: str
    position: str
    size: str
    touchscreen: str
    accept_focus: str
    function_key: str
    source_row: str


class AlarmRecord(TypedDict):
    """One basic alarm definition."""

    trigger: str
    alarm_type: str
    edge_detection: str
    value: str
    deadband_mode: str
    deadband_level: str
    message: str
    source_row: str


class ControllerRecord(TypedDict):
    """One configured communication controller."""

    name: str
    controller_type: str
    address: str
    description: str
    response_timeout_ms: str
    fail_after: str
    connection_timeout_s: str
    inter_request_delay_ms: str
    source_row: str


class Communications(TypedDict):
    """Protocol settings and configured controllers."""

    protocol: str
    connection_type: str
    controllers: list[ControllerRecord]


class ReportSummary(TypedDict):
    """Counts computed from normalized evidence."""

    external_tag_count: int
    tag_types: dict[str, int]
    screen_count: int
    screen_object_count: int
    alarm_count: int


class SectionContractResult(TypedDict):
    """Compatibility result for one semantic report section."""

    section: str
    required: bool
    status: str
    missing_table_headers: list[list[str]]
    missing_setting_labels: list[str]


class Diagnostics(TypedDict):
    """Workbook coverage and semantic compatibility diagnostics."""

    worksheet_count: int
    worksheet_names: list[str]
    recognized_report_sections: list[str]
    unrecognized_report_sections: list[str]
    section_contracts: list[SectionContractResult]
    warnings: list[str]


class CCWReport(TypedDict):
    """Complete loss-preserving and normalized CCW report."""

    schema_version: str
    source: SourceEvidence
    application: ApplicationIdentity
    summary: ReportSummary
    communications: Communications
    diagnostics: Diagnostics
    tags: list[TagRecord]
    screens: list[ScreenRecord]
    screen_objects: list[ScreenObjectRecord]
    alarms: list[AlarmRecord]
    raw_sheets: Workbook
