"""Pytest session configuration."""

from itertools import product
from pathlib import Path
from typing import Generator, List, Tuple

import pytest
import rasterio as rio
from natsort import natsorted
from rasterio import transform, windows


def get_tile_size(ds: rio.DatasetReader) -> int:
    """Return the size tile corresponding to the giveb file.

    .. warning::
        The file must be squared.

    Args:
        ds: the rasterio dataset

    Returns:
        the square size
    """
    return int(ds.width / 4), int(ds.height / 4)


def get_tiles(
    ds: rio.DatasetReader, size: Tuple[int, int]
) -> Generator[int, windows.Window, transform.Affine]:
    """Return the window and transformed associated to a tile from a given dataset.

    Args:
        ds: the rasterio dataset
        size: the tile size
    """
    xsize, ysize = size
    nols, nrows = ds.width, ds.height
    offsets = product(range(0, nols, xsize), range(0, nrows, ysize))
    big_window = windows.Window(col_off=0, row_off=0, width=nols, height=nrows)
    for col_off, row_off in offsets:
        window = windows.Window(
            col_off=col_off, row_off=row_off, width=xsize, height=ysize
        ).intersection(big_window)
        transform = windows.transform(window, ds.transform)
        yield window, transform


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """Returns the data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def tiles(data_dir: Path) -> List[Path]:
    """Returns the list of tiles from the data folder as relative path."""
    # download the data from the rasterio repository
    rio_data = "https://github.com/rasterio/rasterio/raw/main/tests/data/RGB.byte.tif"

    # split the data in tiles in 2 resolutions
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    # create a list of files
    with rio.open(rio_data) as src:
        profile = src.profile.copy()
        size = get_tile_size(src)

        for i, tile in enumerate(get_tiles(src, size)):
            window, affine = tile
            profile.update(transform=affine, width=window.width, height=window.height)
            file = raw_dir / f"tile{i}.tiff"
            with rio.open(file, "w", **profile) as dst:
                dst.write(src.read(window=window))

    # yield the sorted list
    tiles = [f for f in raw_dir.glob("*.tiff")]
    yield natsorted(tiles)

    # flush the folder
    [f.unlink() for f in tiles]
    raw_dir.rmdir()
