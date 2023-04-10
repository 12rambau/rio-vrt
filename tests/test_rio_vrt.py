"""Test the rio_vrt package."""
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

import xmlschema

import rio_vrt


def test_build_vrt_shema(tiles) -> None:
    """Ensure the build vrt is respecting GDAL shema.

    Args:
        tiles: the list of tile path
        file_regression: the pytest regression file fixture
    """
    with NamedTemporaryFile(suffix=".vrt") as vrt_path:
        vrt_file = rio_vrt.build_vrt(vrt_path.name, tiles)
        xsd_file = (
            "https://raw.githubusercontent.com/OSGeo/gdal/master/data/gdalvrt.xsd"
        )
        xml_schema = xmlschema.XMLSchema(urlopen(xsd_file))
        assert xml_schema.is_valid(vrt_file)


def test_build_vrt_complete(tiles, file_regression) -> None:
    """Test a complete vrt where all tiles are touching each other.

    Args:
        tiles: the list of tile path
        file_regression: the pytest regression file fixture
    """
    with NamedTemporaryFile(suffix=".vrt") as vrt_path:
        file = rio_vrt.build_vrt(vrt_path.name, tiles)
        file_regression.check(
            file.read_text(), basename="complete_vrt", extension=".vrt"
        )


def test_build_vrt_hollow(tiles, file_regression) -> None:
    """Test a complete vrt where some tiles are missing.

    Args:
        tiles: the list of tile path
        file_regression: the pytest regression file fixture
    """
    # filter only the pair tiles
    tiles = [t for i, t in enumerate(tiles) if i % 2]
    with NamedTemporaryFile(suffix=".vrt") as vrt_path:
        file = rio_vrt.build_vrt(vrt_path.name, tiles)
        file_regression.check(file.read_text(), basename="hollow_vrt", extension=".vrt")