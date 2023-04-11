"""Pytest session configuration."""

from pathlib import Path
from typing import List

import pytest
from natsort import natsorted


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Returns the data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def tiles(data_dir: Path) -> List[Path]:
    """Returns the list of tiles from the data folder as relative path."""
    tiles = [f for f in data_dir.glob("*.tiff")]
    return natsorted(tiles)
