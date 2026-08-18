"""OLE compound-file adapter used by the RSS inventory service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

import olefile

from rockwell_file_research.rss.errors import RSSInventoryError

OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")


@dataclass(frozen=True)
class CompoundMetadata:
    """Normalized metadata obtained from an OLE property set."""

    creating_application: str = ""
    created_at: datetime | None = None
    last_saved_at: datetime | None = None


class CompoundDocument(Protocol):
    """Minimal compound-document interface required by RSS inventorying."""

    def stream_paths(self) -> list[str]:
        """Return every stream path in deterministic order."""

        ...

    def storage_paths(self) -> list[str]:
        """Return every storage path in deterministic order."""

        ...

    def read_stream(self, path: str) -> bytes:
        """Read one complete stream without interpreting its payload."""

        ...

    def metadata(self) -> CompoundMetadata:
        """Return normalized compound-file metadata."""

        ...


def _decode_property(value: bytes | str | None) -> str:
    """Decode an OLE string property without leaking Python byte syntax."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value.rstrip("\x00")
    return value.decode("utf-8", errors="replace").rstrip("\x00")


class OleCompoundDocument:
    """Read-only adapter around ``olefile.OleFileIO``."""

    def __init__(self, path: Path) -> None:
        try:
            self._ole = olefile.OleFileIO(str(path))
        except OSError as error:
            raise RSSInventoryError(
                f"invalid OLE compound file: {path.name}"
            ) from error

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._ole.close()

    @staticmethod
    def _join(parts: list[str]) -> str:
        return "/".join(parts)

    @staticmethod
    def _split(path: str) -> list[str]:
        return path.split("/")

    def stream_paths(self) -> list[str]:
        """Return all OLE stream paths in deterministic order."""

        return sorted(
            self._join(parts)
            for parts in self._ole.listdir(streams=True, storages=False)
        )

    def storage_paths(self) -> list[str]:
        """Return all OLE storage paths in deterministic order."""

        return sorted(
            self._join(parts)
            for parts in self._ole.listdir(streams=False, storages=True)
        )

    def read_stream(self, path: str) -> bytes:
        """Read an OLE stream by its slash-separated path."""

        return self._ole.openstream(self._split(path)).read()

    def metadata(self) -> CompoundMetadata:
        """Read the standard OLE summary information property set."""

        metadata = self._ole.get_metadata()
        return CompoundMetadata(
            creating_application=_decode_property(
                getattr(metadata, "creating_application", None)
            ),
            created_at=getattr(metadata, "create_time", None),
            last_saved_at=getattr(metadata, "last_saved_time", None),
        )


def verify_ole_signature(path: Path) -> None:
    """Fail clearly when a source is not an OLE compound file."""

    try:
        signature = path.read_bytes()[: len(OLE_SIGNATURE)]
    except OSError as error:
        raise RSSInventoryError(f"could not read source: {path.name}") from error
    if signature != OLE_SIGNATURE:
        raise RSSInventoryError(f"source is not an OLE compound file: {path.name}")
