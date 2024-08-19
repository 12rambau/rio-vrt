"""Test the rio_vrt package."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List
from urllib.request import urlopen

import numpy as np
import pytest
import rasterio as rio
import xmlschema
from bs4 import BeautifulSoup
from rasterio.crs import CRS

import rio_vrt

_xsd_file = (
    "https://raw.githubusercontent.com/OSGeo/gdal/master/frmts/vrt/data/gdalvrt.xsd"
)


def test_build_vrt_html_shema(tiles: List[Path], data_dir: Path) -> None:
    """Ensure the build vrt is respecting GDAL shema.

    Args:
        tiles: the list of tile path
        data_dir: the data directory
    """
    with NamedTemporaryFile(suffix=".vrt", dir=data_dir) as vrt_path:
        vrt_file = rio_vrt.build_vrt(vrt_path.name, tiles)
        xml_schema = xmlschema.XMLSchema(urlopen(_xsd_file))
        assert xml_schema.validate(vrt_file) is None


def test_build_vrt_stack_shema(tiles: List[Path], data_dir: Path) -> None:
    """Ensure the build vrt is respecting GDAL shema.

    Args:
        tiles: the list of tile path
        data_dir: the data directory
    """
    with NamedTemporaryFile(suffix=".vrt", dir=data_dir) as vrt_path:
        vrt_file = rio_vrt.build_vrt(vrt_path.name, tiles, mosaic=False)
        xml_schema = xmlschema.XMLSchema(urlopen(_xsd_file))
        assert xml_schema.validate(vrt_file) is None


def test_build_vrt_complete(tiles: List[Path], data_dir: Path, file_regression) -> None:
    """Test a complete vrt where all tiles are touching each other.

    Args:
        tiles: the list of tile path
        data_dir: the data directory
        file_regression: the pytest regression file fixture
    """
    with NamedTemporaryFile(suffix=".vrt", dir=data_dir) as vrt_path:
        file = rio_vrt.build_vrt(vrt_path.name, tiles, relative=True)
        vrt_tree = BeautifulSoup(file.read_text(), "xml").prettify()
        file_regression.check(vrt_tree, basename="complete_vrt", extension=".vrt")


def test_build_vrt_hollow(tiles: List[Path], data_dir: Path, file_regression) -> None:
    """Test a complete vrt where some tiles are missing.

    Args:
        tiles: the list of tile path
        data_dir: the data directory
        file_regression: the pytest regression file fixture
    """
    # filter only the pair tiles
    tiles = [t for i, t in enumerate(tiles) if i % 2]
    with NamedTemporaryFile(suffix=".vrt", dir=data_dir) as vrt_path:
        file = rio_vrt.build_vrt(vrt_path.name, tiles, relative=True)
        vrt_tree = BeautifulSoup(file.read_text(), "xml").prettify()
        file_regression.check(vrt_tree, basename="hollow_vrt", extension=".vrt")


def test_build_vrt_stack(tiles: List[Path], data_dir: Path, file_regression) -> None:
    """Test a complete vrt where some tiles are missing.

    Args:
        tiles: the list of tile path
        data_dir: the data directory
        file_regression: the pytest regression file fixture
    """
    # filter only the pair tiles
    tiles = [t for i, t in enumerate(tiles) if i % 2]
    with NamedTemporaryFile(suffix=".vrt", dir=data_dir) as vrt_path:
        file = rio_vrt.build_vrt(vrt_path.name, tiles, relative=True, mosaic=False)
        vrt_tree = BeautifulSoup(file.read_text(), "xml").prettify()
        file_regression.check(vrt_tree, basename="stack_vrt", extension=".vrt")


def test_vrt_empty() -> None:
    """Test that an error is raised when the tile list is empty."""
    with pytest.raises(ValueError):
        rio_vrt.build_vrt("error.vrt", [])


def test_vrt_wrong_resolution(tiles: List[Path]) -> None:
    """Test that not all keyword can be used as resolution.

    Args:
        tiles: the list of tile path
    """
    with pytest.raises(ValueError):
        rio_vrt.build_vrt("error.vrt", tiles, res="error")


def test_vrt_wrong_crs(tiles: List[Path]) -> None:
    """Test that you can't create a vrt from varrious crs.

    Args:
        tiles: the list of tile path
    """
    # create an extra tile with a different crs
    with NamedTemporaryFile(suffix=".tiff") as extra_image:
        with rio.open(tiles[0]) as src:
            kwargs = src.meta.copy()
            kwargs.update(crs=CRS.from_epsg(4326))
            data = src.read()

        with rio.open(extra_image.name, "w", **kwargs) as dst:
            dst.write(data)

        # add this tile to the list and check that an error is raised
        with pytest.raises(ValueError):
            new_tiles = tiles + [extra_image.name]
            rio_vrt.build_vrt("error.vrt", new_tiles)


def test_vrt_wrong_count(tiles: List[Path]) -> None:
    """Test that you can't create a vrt mosaic from file with different band count.

    Args:
        tiles: the list of tile path
    """
    # create an extra tile with a different crs
    with NamedTemporaryFile(suffix=".tiff") as extra_image:
        with rio.open(tiles[0]) as src:
            kwargs = src.meta.copy()
            kwargs.update(count=src.count + 1)
            data = src.read()
            new_data = np.expand_dims(np.zeros(data[0].shape), axis=0)
            new_data = np.concatenate((data, new_data), axis=0)

        with rio.open(extra_image.name, "w", **kwargs) as dst:
            dst.write(new_data)

        # add this tile to the list and check that an error is raised
        with pytest.raises(ValueError):
            new_tiles = tiles + [extra_image.name]
            rio_vrt.build_vrt("error.vrt", new_tiles)


@pytest.mark.parametrize("res", ["highest", "average", "lowest", (6, 6)])
def test_vrt_resolutions(
    tiles: List[Path], data_dir: Path, file_regression, res
) -> None:
    """Test vrt with all the available resolution options.

    Args:
        tiles: the list of tile path
        data_dir: the data directory
        file_regression: the pytest regression file fixture
        res: the resolution parameter
    """
    with NamedTemporaryFile(suffix=".vrt", dir=data_dir) as vrt_path:
        file = rio_vrt.build_vrt(vrt_path.name, tiles, relative=True, res=res)
        vrt_tree = BeautifulSoup(file.read_text(), "xml").prettify()
        file_regression.check(vrt_tree, basename=f"{res}_vrt", extension=".vrt")
