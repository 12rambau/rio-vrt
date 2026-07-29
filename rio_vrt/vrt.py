"""Rasterio based vrt creation."""

import xml.etree.cElementTree as ET
from os.path import relpath
from pathlib import Path
from statistics import mean
from typing import List, Tuple, Union
from xml.dom import minidom

import rasterio as rio
from rasterio.enums import ColorInterp

from .enums import resolutions, types


def _add_source_content(
    Source: ET.Element, src: rio.DatasetReader, type: str, xoff: str, yoff: str
) -> None:
    """Add the content of a sourcefile in xml."""
    width, height = str(src.width), str(src.height)
    blockx = str(src.profile.get("blockxsize", ""))
    blocky = str(src.profile.get("blockysize", ""))

    attr = {
        "RasterXSize": width,
        "RasterYSize": height,
        "DataType": type,
    }

    # optional attributes
    if blockx and blocky:
        attr["BlockXSize"], attr["BlockYSize"] = blockx, blocky

    ET.SubElement(Source, "SourceProperties", attr)

    attr = {"xOff": "0", "yOff": "0", "xSize": width, "ySize": height}
    ET.SubElement(Source, "SrcRect", attr)

    attr = {"xOff": xoff, "yOff": yoff, "xSize": width, "ySize": height}
    ET.SubElement(Source, "DstRect", attr)


def build_vrt(
    vrt_path: Union[str, Path],
    files: List[Union[str, Path]],
    relative: bool = False,
    mosaic: bool = True,
    res: Union[str, Tuple[float, float]] = "average",
) -> Path:
    """Create a vrt file from multiple files.

    Arguments:
        vrt_path: the final vrt file
        files: a list of rasterio readable files
        relative: use a path relative to the vrt file. The files path must be relative to the vrt.
        mosaic: The method to use to gather images in the vrt. ``MOSAIC`` (True) will mosaic each band of each image together. ``STACK`` (False) will create one band for each file using the first band of each file.*
        res: The resolution to use in the vrt geotransform. You can use a string (average, highest or lowest) or use a defined tuple of values (xres, yres).

    Returns:
        the path to the vrt file
    """
    # transform the final file in Path
    vrt_path = Path(vrt_path).resolve()

    # transform all the file path into Path objects
    files = [Path(f).resolve() for f in files]

    # cannot do anything if there are no files
    if len(files) == 0:
        raise ValueError("There should be at least 1 file to create a vrt.")

    # check the res value
    if isinstance(res, str) and res not in resolutions:
        raise ValueError(
            'the provided resolution cannot be use: "{res}", please use one of the existing keywords'
        )

    # read global informations from the first file
    with rio.open(files[0]) as f:
        crs = f.crs
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
    left_, bottom_, right_, top_, xres_, yres_ = [], [], [], [], [], []
    for file in files:
        with rio.open(file) as f:
            xres_.append(f.res[0])
            yres_.append(f.res[0])
            left_.append(f.bounds.left)
            right_.append(f.bounds.right)
            top_.append(f.bounds.top)
            bottom_.append(f.bounds.bottom)

    # get the spatial extend of the dataset
    left = min(left_)
    bottom = min(bottom_)
    right = max(right_)
    top = max(top_)

    # get the resolution
    if res == "highest":
        xres, yres = max(xres_), max(yres_)
    elif res == "lowest":
        xres, yres = min(xres_), min(yres_)
    elif res == "average":
        xres, yres = mean(xres_), mean(yres_)
    elif isinstance(res, tuple):
        xres, yres = res

    # rebuild the affine transformation from gathered information along with total bounds
    # negative y_res as we start from the top-left corner
    transform = rio.Affine.from_gdal(left, xres, 0, top, 0, -yres)
    total_width = round((right - left) / xres)
    total_height = round((top - bottom) / yres)

    # start the tree
    attr = {"rasterXSize": str(total_width), "rasterYSize": str(total_height)}
    VRTDataset = ET.Element("VRTDataset", attr)

    # don't know how to extract dataAxisToSRSAxisMapping
    # https://gis.stackexchange.com/questions/458781/how-to-get-dataaxistosrsaxismapping-from-an-image
    # revert to OAMS_TRADITIONAL_GIS_ORDER  until then
    ET.SubElement(VRTDataset, "SRS").text = crs.wkt

    text = ", ".join([str(i) for i in transform.to_gdal()])
    ET.SubElement(VRTDataset, "GeoTransform").text = text

    ET.SubElement(VRTDataset, "OverviewList", {"resampling": "nearest"}).text = "2 4 8"

    # add the rasterbands

    # mosaicking create 1 band for each band of the images and add al the fils as
    # simple sources along with color informations
    if mosaic:
        VRTRasterBands_dict = {}
        for i in indexes:
            attr = {"dataType": types[dtypes[i - 1]], "band": str(i)}
            VRTRasterBands_dict[i] = ET.SubElement(VRTDataset, "VRTRasterBand", attr)

            ET.SubElement(VRTRasterBands_dict[i], "Offset").text = "0.0"

            ET.SubElement(VRTRasterBands_dict[i], "Scale").text = "1.0"

            if colorinterps[i - 1] != ColorInterp.undefined:
                color = colorinterps[i - 1].name.capitalize()
                ET.SubElement(VRTRasterBands_dict[i], "ColorInterp").text = color

            if nodatavals[i - 1] is not None:
                text = str(nodatavals[i - 1])
                ET.SubElement(VRTRasterBands_dict[i], "NoDataValue").text = text

        # add the files
        for f in files:
            relativeToVRT = "1" if relative is True else "0"
            with rio.open(f) as src:
                for i in indexes:
                    is_alpha = colorinterps[i - 1] == ColorInterp.alpha
                    has_nodata = nodatavals[i - 1] is not None
                    source_type = (
                        "ComplexSource" if is_alpha or has_nodata else "SimpleSource"
                    )
                    Source = ET.SubElement(VRTRasterBands_dict[i], source_type)

                    attr = {"relativeToVRT": relativeToVRT}
                    text = str(f) if not relative else relpath(f, vrt_path.parent)
                    ET.SubElement(Source, "SourceFilename", attr).text = text

                    ET.SubElement(Source, "SourceBand").text = str(i)

                    _add_source_content(
                        Source=Source,
                        src=src,
                        type=types[dtypes[i - 1]],
                        xoff=str(abs(round((src.bounds.left - left) / xres))),
                        yoff=str(abs(round((src.bounds.top - top) / yres))),
                    )

                    if nodatavals[i - 1] is not None:
                        text = str(nodatavals[i - 1])
                        ET.SubElement(Source, "NODATA").text = text

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
            text = str(f) if not relative else relpath(f, vrt_path.parent)
            ET.SubElement(ComplexSource, "SourceFilename", attr).text = text

            ET.SubElement(ComplexSource, "SourceBand").text = "1"

            with rio.open(f) as src:
                _add_source_content(
                    Source=ComplexSource,
                    src=src,
                    type=types[dtypes[0]],
                    xoff=str(abs(round((src.bounds.left - left) / xres))),
                    yoff=str(abs(round((src.bounds.top - top) / yres))),
                )

    # write the file
    vrt_path.resolve().write_text(
        minidom.parseString(ET.tostring(VRTDataset).decode("utf-8"))
        .toprettyxml(indent="  ")
        .replace("&quot;", '"')
    )

    return vrt_path
