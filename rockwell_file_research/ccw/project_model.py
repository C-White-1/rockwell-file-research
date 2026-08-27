"""Build a deterministic vendor-neutral project model from CCW evidence."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from rockwell_file_research.ccw.archive import inspect_ccwarc
from rockwell_file_research.ccw.cross_reference import build_cross_reference
from rockwell_file_research.ccw.ladder import (
    GridPosition,
    LadderInstruction,
    LadderParallel,
    LadderSeries,
    parse_stf,
)

SCHEMA_VERSION = "ccw-project-v1"


def build_project_model(
    source: str | Path, *, source_label: str | None = None
) -> dict[str, Any]:
    """Normalize a CCW archive without discarding source evidence."""

    inventory = inspect_ccwarc(source)
    cross_reference = build_cross_reference(source)
    with zipfile.ZipFile(source) as archive:
        programs = []
        for entry in sorted(
            name for name in archive.namelist() if name.lower().endswith(".stf")
        ):
            program = parse_stf(
                archive.read(entry).decode("utf-8-sig", errors="replace")
            )
            programs.append(
                {
                    "name": program.name,
                    "language": program.language,
                    "source_entry": entry,
                    "rungs": [
                        {
                            "number": number,
                            "position": _position(rung.position),
                            "network": _series(rung.network),
                            "raw_sha256": _sha256(rung.raw),
                        }
                        for number, rung in enumerate(program.rungs, start=1)
                    ],
                    "diagnostics": list(program.diagnostics),
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "reference": source_label or inventory.source,
            "size": inventory.size,
            "sha256": inventory.sha256,
            "entry_count": inventory.entry_count,
        },
        "project": {
            "name": inventory.project_name,
            "engineering_tool": "Connected Components Workbench",
            "engineering_tool_version": inventory.ccw_version,
        },
        "controller": {
            "catalog_number": inventory.controller_catalog,
            "simulated": inventory.simulator_target,
        },
        "programs": programs,
        "variables": [
            {
                "name": item.variable.name,
                "scope": item.variable.scope,
                "classification": item.variable.kind,
                "data_type": item.variable.data_type,
                "aliases": list(item.variable.aliases),
                "physical_source": item.variable.physical_source,
                "physical_destination": item.variable.physical_destination,
                "evidence_entries": list(item.variable.evidence_entries),
                "usages": [
                    {
                        "program": usage.program,
                        "rung": usage.rung,
                        "branch_path": list(usage.branch_path),
                        "mnemonic": usage.mnemonic,
                        "access": usage.access,
                        "position": _position(usage.position),
                    }
                    for usage in item.usages
                ],
                "seal_in_rungs": [
                    {"program": program, "rung": rung}
                    for program, rung in item.seal_in_rungs
                ],
            }
            for item in cross_reference.variables
        ],
        "unresolved_operands": list(cross_reference.unresolved_operands),
        "diagnostics": list(cross_reference.diagnostics),
        "evidence": {
            "sensitive_entries": list(inventory.sensitive_entries),
            "unknown_entries": list(inventory.unknown_entries),
        },
    }


def write_project_model(model: dict[str, Any], destination: str | Path) -> None:
    """Write deterministic UTF-8 JSON for downstream consumers."""

    Path(destination).write_text(
        json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _series(series: LadderSeries) -> dict[str, Any]:
    return {
        "kind": "series",
        "elements": [
            _instruction(element)
            if isinstance(element, LadderInstruction)
            else _parallel(element)
            for element in series.elements
        ],
    }


def _parallel(parallel: LadderParallel) -> dict[str, Any]:
    return {
        "kind": "parallel",
        "branches": [_series(item) for item in parallel.branches],
    }


def _instruction(instruction: LadderInstruction) -> dict[str, Any]:
    return {
        "kind": "instruction",
        "mnemonic": instruction.mnemonic,
        "operand": instruction.operand,
        "alias": instruction.alias,
        "annotations": list(instruction.annotations),
        "position": _position(instruction.position),
    }


def _position(position: GridPosition | None) -> dict[str, int] | None:
    if position is None:
        return None
    return {"column": position.column, "row": position.row}


def _sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
