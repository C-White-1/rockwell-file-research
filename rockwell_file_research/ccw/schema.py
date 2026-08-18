"""Load and validate the versioned JSON representation of a CCW report."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from rockwell_file_research.ccw.errors import (
    ReportSchemaError,
    ReportValidationUnavailableError,
)
from rockwell_file_research.ccw.models import CCWReport

SCHEMA_NAME = "ccw-report-v1.schema.json"


def load_schema() -> dict[str, Any]:
    """Load the packaged CCW report schema."""

    resource = files("rockwell_file_research.ccw.schemas").joinpath(SCHEMA_NAME)
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_report(report: CCWReport) -> None:
    """Validate a report, requiring the optional validation dependency."""

    try:
        from jsonschema import Draft202012Validator, SchemaError, ValidationError
    except ImportError as error:
        raise ReportValidationUnavailableError(
            "JSON Schema validation requires the 'validation' extra: "
            "uv sync --extra validation"
        ) from error

    schema = load_schema()
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)
    except (SchemaError, ValidationError) as error:
        raise ReportSchemaError(
            f"generated report failed JSON Schema validation: {error.message}"
        ) from error
