"""Compatibility entry point for the packaged CCW report command."""

from rockwell_file_research.ccw import build_report, export_report
from rockwell_file_research.ccw.cli import main

__all__ = ["build_report", "export_report", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
