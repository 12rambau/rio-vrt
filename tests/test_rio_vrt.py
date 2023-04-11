"""Test the rio_vrt package."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List
from urllib.request import urlopen

import xmlschema
from bs4 import BeautifulSoup

import rio_vrt


def test_build_vrt_shema(tiles: List[Path], data_dir: Path) -> None:
    """Ensure the build vrt is respecting GDAL shema.

    Args:
        tiles: the list of tile path
        data_dir: the data directory
    """
    with NamedTemporaryFile(suffix=".vrt", dir=data_dir) as vrt_path:
        vrt_file = rio_vrt.build_vrt(vrt_path.name, tiles)
        xsd_file = (
            "https://raw.githubusercontent.com/OSGeo/gdal/master/data/gdalvrt.xsd"
        )
        xml_schema = xmlschema.XMLSchema(urlopen(xsd_file))
        assert xml_schema.is_valid(vrt_file)


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
