"""Pytest session configuration."""

from pathlib import Path
from typing import List

import pytest
from natsort import natsorted


@pytest.fixture(scope="session")
def tiles() -> List[Path]:
    """Returns the list of tiles from the data folder."""
    data_dir = Path(__file__).parent / "data"
    tiles = [f for f in data_dir.glob("*.tiff")]
    return natsorted(tiles)
