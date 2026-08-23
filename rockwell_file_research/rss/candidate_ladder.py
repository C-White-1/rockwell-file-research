"""Human-readable rendering of probable RSS instruction sequences."""

from collections import defaultdict

from rockwell_file_research.rss.models import (
    RSSInventory,
    RSSProgramInstructionCandidateEvidence,
    RSSRungTopologyEvidence,
    RSSRungTopologyInstruction,
    RSSRungTopologyParallel,
)


def _operand_label(candidate: RSSProgramInstructionCandidateEvidence) -> str:
    values = []
    for operand in candidate["operands"]:
        if operand["access"] == "metadata":
            continue
        values.append(operand["value"] or f"sha256:{operand['sha256'][:12]}")
    return ", ".join(values)


def _instruction_label(candidate: RSSProgramInstructionCandidateEvidence) -> str:
    mnemonic = candidate["proposed_mnemonic"]
    operand = _operand_label(candidate)
    if mnemonic == "UNKNOWN":
        selector = candidate["selector"]
        return f"[UNKNOWN 0x{selector:02X} ({selector}) {operand}]"
    if mnemonic == "XIC":
        return f"[?XIC {operand}]"
    if mnemonic == "XIO":
        return f"[?XIO {operand}]"
    if mnemonic == "OTE":
        return f"(?OTE {operand})"
    if mnemonic == "OTL":
        return f"(?OTL {operand})"
    if mnemonic == "OTU":
        return f"(?OTU {operand})"
    return f"[?{mnemonic} {operand}]"


def _render_topology_items(
    items: list[RSSRungTopologyInstruction | RSSRungTopologyParallel],
    candidates: dict[int, RSSProgramInstructionCandidateEvidence],
) -> str:
    rendered = []
    for item in items:
        if item["kind"] == "instruction":
            candidate = candidates.get(item["selector_offset"])
            rendered.append(
                _instruction_label(candidate)
                if candidate is not None
                else f"[{item['mnemonic']} ?]"
            )
        else:
            legs = [_render_topology_items(leg, candidates) for leg in item["legs"]]
            rendered.append("{ " + " || ".join(legs) + " }")
    return "--".join(rendered)


def render_probable_ladder_markdown(inventory: RSSInventory) -> str:
    """Render ordered candidates by rung without inventing branch topology."""

    grouped: dict[
        tuple[int | None, str | None, str | None, int | None],
        list[RSSProgramInstructionCandidateEvidence],
    ] = defaultdict(list)
    for candidate in inventory["program_files"]["instruction_candidates"]:
        key = (
            candidate["program_file_number"],
            candidate["program_file_name"],
            candidate["program_file_name_sha256"],
            candidate["rung_index"],
        )
        grouped[key].append(candidate)
    rung_topologies: dict[
        tuple[int | None, str | None, str | None, int | None],
        RSSRungTopologyEvidence | None,
    ] = {}
    for rung in inventory["program_files"].get("rung_records", []):
        rung_key: tuple[int | None, str | None, str | None, int | None] = (
            rung["program_file_number"],
            rung["program_file_name"],
            rung["program_file_name_sha256"],
            rung["rung_index"],
        )
        rung_topologies[rung_key] = rung["candidate_topology"]

    lines = [
        "# Probable ladder instruction view",
        "",
        "> **Disclaimer:** This is an evidence view, not reconstructed source.",
        "> `?MNEMONIC` identities are probable. ML1400 branch topology is generally",
        "> unresolved, and unsupported instructions may be omitted. Apparent series",
        "> order is serialized record order, not proven electrical continuity.",
        "> `UNKNOWN 0xNN (N)` preserves an unclassified selector in hexadecimal",
        "> and decimal; it does not assign an instruction mnemonic.",
        "> Do not use this output for control changes.",
        "",
        "Legend: `[?XIC X]` contact candidate; `[?XIO X]` normally-closed",
        "contact candidate; `(?OTE X)` coil candidate; `{ A || B }` decoded",
        "parallel candidate legs.",
        "",
    ]
    for key in sorted(
        grouped,
        key=lambda item: (
            item[0] if item[0] is not None else 1_000_000,
            item[3] if item[3] is not None else 1_000_000,
        ),
    ):
        file_number, file_name, file_name_hash, rung_index = key
        name = file_name or (
            f"sha256:{file_name_hash[:12]}" if file_name_hash else "unknown"
        )
        rung = "unknown" if rung_index is None else str(rung_index)
        ordered = sorted(grouped[key], key=lambda item: item["selector_offset"])
        by_offset = {item["selector_offset"]: item for item in ordered}
        topology = rung_topologies.get(key)
        expression = (
            _render_topology_items(topology["items"], by_offset)
            if topology is not None
            else "--".join(_instruction_label(item) for item in ordered)
        )
        has_parallel = topology is not None and topology["kind"] == "series_parallel"
        topology_note = (
            "Topology: probable candidate branch structure."
            if has_parallel
            else "Topology: unresolved; serialized record order only."
        )
        lines.extend(
            (
                f"## Program {file_number}: {name} — rung {rung}",
                "",
                "```text",
                f"|--{expression}--|",
                "```",
                "",
                topology_note,
                "",
            )
        )
    return "\n".join(lines)
