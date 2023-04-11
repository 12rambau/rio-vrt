"""Cut an image in 16 tiles (4x4) to use in the tests."""

import argparse
from itertools import product
from pathlib import Path
from typing import Generator

import rasterio as rio
from rasterio import transform, windows

HERE = Path(__file__).parent


def get_tile_size(ds: rio.DatasetReader) -> int:
    """Return the size tile corresponding to the giveb file.

    .. warning::
        The file must be squared.

    Args:
        ds: the rasterio dataset

    Returns:
        the square size
    """
    assert ds.width == ds.height, "Cannot cut images that are not squared"
    return int(ds.width / 4)


def get_tiles(
    ds: rio.DatasetReader, size: int
) -> Generator[int, windows.Window, transform.Affine]:
    """Return the window and transformed associated to a tile from a given dataset.

    Args:
        ds: the rasterio dataset
        size: the tile size
    """
    nols, nrows = ds.width, ds.height
    offsets = product(range(0, nols, size), range(0, nrows, size))
    big_window = windows.Window(col_off=0, row_off=0, width=nols, height=nrows)
    for col_off, row_off in offsets:
        window = windows.Window(
            col_off=col_off, row_off=row_off, width=size, height=size
        ).intersection(big_window)
        transform = windows.transform(window, ds.transform)
        yield window, transform


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__, usage="cut_image")
    parser.add_argument(
        "-i",
        dest="src_rst",
        metavar="source.tif",
        help="(str) : path to the source raster",
        required=True,
        type=Path,
    )
    args = parser.parse_args()

    # build and save the tiles in the data folder
    with rio.open(args.src_rst) as src:

        # copy the meta for further use
        profile = src.profile.copy()
        size = get_tile_size(src)

        for i, tile in enumerate(get_tiles(src, size)):
            window, affine = tile
            profile.update(transform=affine, width=window.width, height=window.height)
            file = HERE / f"tile_{i}.tiff"
            with rio.open(file, "w", **profile) as dst:
                dst.write(src.read(window=window))
