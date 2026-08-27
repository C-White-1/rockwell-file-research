"""Render CCW archive engineering evidence as deterministic Markdown."""

from __future__ import annotations

from rockwell_file_research.ccw.archive import CCWArchiveInventory
from rockwell_file_research.ccw.cross_reference import CCWCrossReferenceReport


def render_ccw_archive_markdown(
    inventory: CCWArchiveInventory,
    report: CCWCrossReferenceReport,
    *,
    source_label: str | None = None,
) -> str:
    """Render a privacy-aware project, variable and usage report."""

    label = source_label or inventory.source
    user_variables = [item for item in report.variables if item.variable.kind == "user"]
    lines = [
        "<!-- markdownlint-disable MD013 -->",
        "",
        "# CCW archive engineering report",
        "",
        "> Read-only structural evidence. Verify inferred engineering meaning",
        "> against the source project before operational use.",
        "",
        "## Project summary",
        "",
        f"- Source: `{_text(label)}`",
        f"- SHA-256: `{inventory.sha256}`",
        f"- CCW version: {inventory.ccw_version or 'unknown'}",
        f"- Project: {_text(inventory.project_name)}",
        f"- Controller: `{inventory.controller_catalog or 'unknown'}`",
        f"- Simulator target: {'yes' if inventory.simulator_target else 'no'}",
        f"- Archive entries: {inventory.entry_count}",
        f"- Authored programs: {len(inventory.programs)}",
        f"- User global variables: {len(user_variables)}",
        f"- Unresolved ladder operands: {len(report.unresolved_operands)}",
        f"- Privacy-sensitive entries: {len(inventory.sensitive_entries)}",
        "",
        "## Programs",
        "",
        "| Program | Ladder source | Lowered text | Representations |",
        "| --- | --- | --- | ---: |",
    ]
    for program in inventory.programs:
        lines.append(
            f"| {_cell(program.name)} | {_yes(program.has_ladder_source)} | "
            f"{_yes(program.has_lowered_text)} | {len(program.entries)} |"
        )
    lines.extend(
        [
            "",
            "## User global variables",
            "",
            "| Variable | Type | Alias | Physical source | Physical destination | Reads | Writes | Unknown | Seal-in rungs |",
            "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in user_variables:
        reads = sum(usage.access == "read" for usage in item.usages)
        writes = sum(usage.access == "write" for usage in item.usages)
        unknown = sum(usage.access == "unknown" for usage in item.usages)
        seal_ins = ", ".join(
            f"{program} rung {rung}" for program, rung in item.seal_in_rungs
        )
        variable = item.variable
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    variable.name,
                    variable.data_type,
                    ", ".join(variable.aliases),
                    variable.physical_source,
                    variable.physical_destination,
                    reads,
                    writes,
                    unknown,
                    seal_ins,
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Authored ladder references",
            "",
            "| Variable | Program | Rung | Branch | Instruction | Access | Position |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for item in user_variables:
        for usage in item.usages:
            branch = ".".join(str(index + 1) for index in usage.branch_path)
            position = (
                f"{usage.position.column},{usage.position.row}"
                if usage.position
                else ""
            )
            lines.append(
                "| "
                + " | ".join(
                    _cell(value)
                    for value in (
                        item.variable.name,
                        usage.program,
                        usage.rung,
                        branch,
                        usage.mnemonic,
                        usage.access,
                        position,
                    )
                )
                + " |"
            )
    lines.extend(["", "## Diagnostics", ""])
    diagnostics = [*report.diagnostics]
    if report.unresolved_operands:
        diagnostics.append(
            "Unresolved operands: " + ", ".join(report.unresolved_operands)
        )
    if inventory.sensitive_entries:
        diagnostics.append(
            f"Archive contains {len(inventory.sensitive_entries)} privacy-sensitive entries; their contents were not exported."
        )
    if not diagnostics:
        lines.append("No diagnostics.")
    else:
        lines.extend(f"- {_text(item)}" for item in diagnostics)
    return "\n".join(lines) + "\n"


def _cell(value: object) -> str:
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _text(value: object) -> str:
    return str(value or "unknown").replace("\n", " ")


def _yes(value: bool) -> str:
    return "yes" if value else "no"
