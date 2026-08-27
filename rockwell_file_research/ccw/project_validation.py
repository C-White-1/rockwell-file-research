"""JSON Schema validation for the normalized CCW project contract."""

import json
from importlib.resources import files
from typing import Any

SCHEMA_NAME = "ccw-project-v1.schema.json"


def load_project_schema() -> dict[str, Any]:
    """Load the packaged Draft 2020-12 project schema."""

    resource = files("rockwell_file_research.ccw.schemas").joinpath(SCHEMA_NAME)
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_project_model(model: dict[str, Any]) -> None:
    """Validate one normalized project, requiring the validation extra."""

    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise RuntimeError(
            "project validation requires: uv sync --extra validation"
        ) from error
    schema = load_project_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(model)
