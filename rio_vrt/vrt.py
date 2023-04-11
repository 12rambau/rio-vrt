"""Rasterio based vrt creation."""

import xml.etree.cElementTree as ET
from pathlib import Path
from typing import List, Union
from xml.dom import minidom

import rasterio as rio
from rasterio.enums import ColorInterp

from .enums import types


def build_vrt(
    vrt_path: Union[str, Path], files: List[Union[str, Path]], relative: bool = False
) -> Path:
    """Create a vrt file from multiple files.

    Arguments:
        vrt_path: the final vrt file
        files: a list of rasterio readable files
        relative: use a path relative to the vrt file. The files path must be relative to the vrt.

    Returns:
        the path to the vrt file
    """
    # transform the final file in Path
    vrt_path = Path(vrt_path)

    # transform all the file path into Path objects
    files = [Path(f).resolve() for f in files]

    # cannot do anything if there are no files
    if len(files) == 0:
        raise ValueError("There should be at least 1 file to create a vrt.")

    # read global informations from the first file
    with rio.open(files[0]) as f:
        crs = f.crs
        left, bottom, right, top = f.bounds
        x_res, y_res = f.res
        count = f.count
        dtypes = f.dtypes
        colorinterps = f.colorinterp
        indexes = f.indexes
        nodatavals = f.nodatavals

    # sanity checks
    for file in files:
        with rio.open(file) as f:
            if f.crs != crs:
                raise ValueError(
                    f'the crs ({f.crs}) from file "{file}" is not corresponding to the global one ({crs})'
                )

            if f.count != count:
                raise ValueError(
                    f'the crs ({f.count}) from file "{file}" is not corresponding to the global one ({count})'
                )

    # read all files to extract information and perform
    for file in files:
        with rio.open(file) as f:
            left = min(left, f.bounds.left)
            bottom = min(bottom, f.bounds.bottom)
            right = max(right, f.bounds.right)
            top = max(top, f.bounds.top)

        # rebuild the affine transformation from gathered information
        # negative y_res as we start from the top-left corner
        transform = rio.Affine.from_gdal(left, x_res, 0, top, 0, -y_res)

    total_width = round((right - left) / x_res)
    total_height = round((top - bottom) / y_res)

    # start the tree
    VRTDataset = ET.Element(
        "VRTDataset",
        {"rasterXSize": str(total_width), "rasterYSize": str(total_height)},
    )
    ET.SubElement(VRTDataset, "SRS", {"dataAxisToSRSAxisMapping": "2,1"}).text = crs.wkt
    ET.SubElement(VRTDataset, "GeoTransform").text = ", ".join(
        [str(i) for i in transform.to_gdal()]
    )
    ET.SubElement(VRTDataset, "OverviewList", {"resampling": "nearest"}).text = "2 4 8"

    # create the bands subelements
    VRTRasterBands = {}
    for i in indexes:
        VRTRasterBands[i] = ET.SubElement(
            VRTDataset,
            "VRTRasterBand",
            {"dataType": types[dtypes[i - 1]], "band": str(i)},
        )
        ET.SubElement(VRTRasterBands[i], "Offset").text = "0.0"
        ET.SubElement(VRTRasterBands[i], "Scale").text = "1.0"
        if colorinterps[i - 1] != ColorInterp.undefined:
            ET.SubElement(VRTRasterBands[i], "ColorInterp").text = colorinterps[
                i - 1
            ].name.capitalize()

    # add the files
    for f in files:
        relativeToVRT = "1" if relative is True else "0"
        with rio.open(f) as src:
            for i in indexes:
                if colorinterps[i - 1] == ColorInterp.alpha:
                    source_type = "ComplexSource"
                else:
                    source_type = "SimpleSource"

                Source = ET.SubElement(VRTRasterBands[i], source_type)
                ET.SubElement(
                    Source, "SourceFilename", {"relativeToVRT": relativeToVRT}
                ).text = (
                    str(f) if relative is False else str(f.relative_to(vrt_path.parent))
                )
                ET.SubElement(Source, "SourceBand").text = str(i)
                ET.SubElement(
                    Source,
                    "SourceProperties",
                    {
                        "RasterXSize": str(src.width),
                        "RasterYSize": str(src.height),
                        "DataType": types[dtypes[i - 1]],
                        "BlockXSize": str(src.profile["blockxsize"]),
                        "BlockYSize": str(src.profile["blockysize"]),
                    },
                )
                ET.SubElement(
                    Source,
                    "SrcRect",
                    {
                        "xOff": "0",
                        "yOff": "0",
                        "xSize": str(src.width),
                        "ySize": str(src.height),
                    },
                )
                ET.SubElement(
                    Source,
                    "DstRect",
                    {
                        "xOff": str(abs(round((src.bounds.left - left) / x_res))),
                        "yOff": str(abs(round((src.bounds.top - top) / y_res))),
                        "xSize": str(src.width),
                        "ySize": str(src.height),
                    },
                )
                if nodatavals[i - 1] is not None:
                    ET.SubElement(Source, "NoDataValue").text = str(nodatavals[i - 1])

                if colorinterps[i - 1] == ColorInterp.alpha:
                    ET.SubElement(Source, "UseMaskBand").text = "true"

    # write the file
    vrt_path.resolve().write_text(
        minidom.parseString(ET.tostring(VRTDataset).decode("utf-8"))
        .toprettyxml(indent="  ")
        .replace("&quot;", '"')
    )

    return vrt_path
