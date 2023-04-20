"""Rasterio based vrt creation."""

import xml.etree.cElementTree as ET
from pathlib import Path
from typing import List, Union
from xml.dom import minidom

import rasterio as rio
from rasterio.enums import ColorInterp

from .enums import types


def build_vrt(
    vrt_path: Union[str, Path],
    files: List[Union[str, Path]],
    relative: bool = False,
    mosaic: bool = True,
) -> Path:
    """Create a vrt file from multiple files.

    Arguments:
        vrt_path: the final vrt file
        files: a list of rasterio readable files
        relative: use a path relative to the vrt file. The files path must be relative to the vrt.
        mosaic: The method to use to gather images in the vrt. ``MOSAIC`` (True) will mosaic each band of each image together. ``STACK`` (False) will create one band for each file using the first band of each file.

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

    # for stacks replace count and indexes as we only take the first band
    if not mosaic:
        count, indexes = len(files), [1]

    # sanity checks
    for file in files:
        with rio.open(file) as f:
            if f.crs != crs:
                raise ValueError(
                    f'the crs ({f.crs}) from file "{file}" is not corresponding to the global one ({crs})'
                )

            if mosaic and f.count != count:
                raise ValueError(
                    f'the crs ({f.count}) from file "{file}" is not corresponding to the global one ({count})'
                )

    # read all files to extract information on the spatial extend of the vrt
    for file in files:
        with rio.open(file) as f:
            left = min(left, f.bounds.left)
            bottom = min(bottom, f.bounds.bottom)
            right = max(right, f.bounds.right)
            top = max(top, f.bounds.top)

    # rebuild the affine transformation from gathered information along with total bounds
    # negative y_res as we start from the top-left corner
    transform = rio.Affine.from_gdal(left, x_res, 0, top, 0, -y_res)
    total_width = round((right - left) / x_res)
    total_height = round((top - bottom) / y_res)

    # start the tree
    attr = {"rasterXSize": str(total_width), "rasterYSize": str(total_height)}
    VRTDataset = ET.Element("VRTDataset", attr)

    ET.SubElement(VRTDataset, "SRS", {"dataAxisToSRSAxisMapping": "2,1"}).text = crs.wkt

    text = ", ".join([str(i) for i in transform.to_gdal()])
    ET.SubElement(VRTDataset, "GeoTransform").text = text

    ET.SubElement(VRTDataset, "OverviewList", {"resampling": "nearest"}).text = "2 4 8"

    # add the rasterbands

    # mosaicking create 1 band for each band of the images and add al the fils as
    # simple sources along with color informations
    if mosaic:
        VRTRasterBands = {}
        for i in indexes:
            attr = {"dataType": types[dtypes[i - 1]], "band": str(i)}
            VRTRasterBands[i] = ET.SubElement(VRTDataset, "VRTRasterBand", attr)

            ET.SubElement(VRTRasterBands[i], "Offset").text = "0.0"

            ET.SubElement(VRTRasterBands[i], "Scale").text = "1.0"

            if colorinterps[i - 1] != ColorInterp.undefined:
                color = colorinterps[i - 1].name.capitalize()
                ET.SubElement(VRTRasterBands[i], "ColorInterp").text = color

        # add the files
        for f in files:
            relativeToVRT = "1" if relative is True else "0"
            with rio.open(f) as src:
                for i in indexes:
                    is_alpha = colorinterps[i - 1] == ColorInterp.alpha
                    source_type = "ComplexSource" if is_alpha else "SimpleSource"
                    Source = ET.SubElement(VRTRasterBands[i], source_type)

                    attr = {"relativeToVRT": relativeToVRT}
                    text = (
                        str(f) if not relative else str(f.relative_to(vrt_path.parent))
                    )
                    ET.SubElement(Source, "SourceFilename", attr).text = text

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
                        text = str(nodatavals[i - 1])
                        ET.SubElement(Source, "NoDataValue").text = text

                    if colorinterps[i - 1] == ColorInterp.alpha:
                        ET.SubElement(Source, "UseMaskBand").text = "true"

    # in stacked vrt, each file is added as a single band and only the first band is
    # considered. They are all complex sources to make sure GIS softwares don't do funny
    # display upon reading
    elif not mosaic:
        for i, f in enumerate(files):
            attr = {"dataType": types[dtypes[0]], "band": str(i)}
            VRTRasterBands = ET.SubElement(VRTDataset, "VRTRasterBand", attr)

            ComplexSource = ET.SubElement(VRTRasterBands, "ComplexSource")

            relativeToVRT = "1" if relative is True else "0"
            attr = {"relativeToVRT": relativeToVRT}
            text = str(f) if relative is False else str(f.relative_to(vrt_path.parent))
            ET.SubElement(ComplexSource, "SourceFilename", attr).text = text

            ET.SubElement(ComplexSource, "SourceBand").text = "1"

            with rio.open(f) as src:
                ET.SubElement(
                    ComplexSource,
                    "SourceProperties",
                    {
                        "RasterXSize": str(src.width),
                        "RasterYSize": str(src.height),
                        "DataType": types[dtypes[0]],
                        "BlockXSize": str(src.profile["blockxsize"]),
                        "BlockYSize": str(src.profile["blockysize"]),
                    },
                )

                ET.SubElement(
                    ComplexSource,
                    "SrcRect",
                    {
                        "xOff": "0",
                        "yOff": "0",
                        "xSize": str(src.width),
                        "ySize": str(src.height),
                    },
                )

                ET.SubElement(
                    ComplexSource,
                    "DstRect",
                    {
                        "xOff": str(abs(round((src.bounds.left - left) / x_res))),
                        "yOff": str(abs(round((src.bounds.top - top) / y_res))),
                        "xSize": str(src.width),
                        "ySize": str(src.height),
                    },
                )

    # write the file
    vrt_path.resolve().write_text(
        minidom.parseString(ET.tostring(VRTDataset).decode("utf-8"))
        .toprettyxml(indent="  ")
        .replace("&quot;", '"')
    )

    return vrt_path
