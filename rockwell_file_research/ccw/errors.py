"""Domain exceptions raised while processing CCW reports."""


class CCWReportError(Exception):
    """Base class for expected, user-facing CCW report failures."""


class WorkbookReadError(CCWReportError):
    """The input is not a readable Office Open XML workbook."""


class UnsupportedWorkbookError(CCWReportError):
    """The workbook does not contain the required CCW report structure."""
