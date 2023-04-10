"""Pytest session configuration."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def tiles() -> list[Path]:
    """Returns the list of tiles from the data folder."""
    data_dir = Path(__file__).parent / "data"
    return [f for f in data_dir.glob("*.tiff")]
