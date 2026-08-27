"""Read-only structural inventorying for Connected Components Workbench archives."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from xml.etree import ElementTree


class CCWArchiveError(ValueError):
    """Raised when a source is not a readable CCW archive."""


@dataclass(frozen=True)
class CCWProgramArtifacts:
    """Known representations belonging to one CCW program."""

    name: str
    entries: tuple[str, ...]
    has_ladder_source: bool
    has_lowered_text: bool


@dataclass(frozen=True)
class CCWArchiveInventory:
    """Privacy-aware structural evidence recovered from one CCW archive."""

    source: str
    size: int
    sha256: str
    entry_count: int
    ccw_version: str | None
    project_name: str | None
    controller_catalog: str | None
    simulator_target: bool
    programs: tuple[CCWProgramArtifacts, ...]
    sensitive_entries: tuple[str, ...]
    unknown_entries: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible representation."""

        return asdict(self)


_PROGRAM_PATTERN = re.compile(
    r"Controller/Controller/[^/]+/[^/]+/(?P<name>[^/]+)\.(?P<suffix>stf|txt|rtc|ic|otc|fmo|AcfMlge)$",
    re.IGNORECASE,
)
_CATALOG_PATTERN = re.compile(rb"2080-[A-Z0-9-]+", re.IGNORECASE)
_KNOWN_SUFFIXES = {
    ".7z",
    ".accdb",
    ".acfmlge",
    ".acfproj",
    ".ain",
    ".ccwsln",
    ".ccwsuo",
    ".cnf",
    ".csv",
    ".err",
    ".fmo",
    ".gpm",
    ".had",
    ".ic",
    ".icp",
    ".ics",
    ".ict",
    ".info",
    ".ipa",
    ".lst",
    ".mtc",
    ".otc",
    ".rtc",
    ".stf",
    ".ttc",
    ".txt",
    ".xml",
    ".xtc",
    ".zip",
}


def inspect_ccwarc(source: str | Path) -> CCWArchiveInventory:
    """Inventory a CCW ZIP archive without extracting its contents."""

    path = Path(source)
    try:
        payload = path.read_bytes()
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise CCWArchiveError(f"not a readable CCW archive: {path}") from error

    with archive:
        names = tuple(sorted(info.filename for info in archive.infolist()))
        revision = _revision_metadata(archive)
        catalog = _controller_catalog(archive)
        programs = _programs(names)
        sensitive = tuple(
            name
            for name in names
            if name.lower().endswith(("devicepref.xml", ".ccwsuo"))
        )
        unknown = tuple(
            name
            for name in names
            if not name.endswith("/")
            and Path(name).suffix.lower() not in _KNOWN_SUFFIXES
        )

    return CCWArchiveInventory(
        source=path.name,
        size=len(payload),
        sha256=hashlib.sha256(payload).hexdigest(),
        entry_count=len(names),
        ccw_version=revision.get("CCWVersion"),
        project_name=revision.get("ProjectName"),
        controller_catalog=catalog,
        simulator_target=bool(catalog and catalog.upper().endswith("-SIM")),
        programs=programs,
        sensitive_entries=sensitive,
        unknown_entries=unknown,
    )


def write_inventory(inventory: CCWArchiveInventory, destination: str | Path) -> None:
    """Write inventory JSON without exporting any archive payload."""

    Path(destination).write_text(
        json.dumps(inventory.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _revision_metadata(archive: zipfile.ZipFile) -> dict[str, str]:
    try:
        root = ElementTree.fromstring(archive.read("RevisionInfo.txt"))
    except (KeyError, ElementTree.ParseError):
        return {}
    return {child.tag: child.text or "" for child in root}


def _controller_catalog(archive: zipfile.ZipFile) -> str | None:
    for name in ("Controller/Controller/persist.ccwx",):
        try:
            match = _CATALOG_PATTERN.search(archive.read(name))
        except KeyError:
            continue
        if match:
            return match.group().decode("ascii")
    return None


def _programs(names: tuple[str, ...]) -> tuple[CCWProgramArtifacts, ...]:
    artifacts = [entry for entry in names if _PROGRAM_PATTERN.fullmatch(entry)]
    source_names = {
        Path(entry).stem.upper()
        for entry in artifacts
        if entry.lower().endswith(".stf")
    }
    grouped = {
        name: [entry for entry in artifacts if Path(entry).stem.upper() == name]
        for name in source_names
    }
    return tuple(
        CCWProgramArtifacts(
            name=name,
            entries=tuple(sorted(entries)),
            has_ladder_source=any(entry.lower().endswith(".stf") for entry in entries),
            has_lowered_text=any(entry.lower().endswith(".txt") for entry in entries),
        )
        for name, entries in sorted(grouped.items())
    )
