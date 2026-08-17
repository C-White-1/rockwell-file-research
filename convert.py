"""Extract the database files contained in a user-supplied Logix ACD file."""

from pathlib import Path

from acd.api import ExtractAcdDatabase


def extract_acd(source: Path, destination: Path) -> None:
    """Extract *source* into *destination* using the installed acd-tools API."""
    ExtractAcdDatabase(source, destination).extract()


if __name__ == "__main__":
    extract_acd(Path("MyController.ACD"), Path("private-outputs/MyController"))
