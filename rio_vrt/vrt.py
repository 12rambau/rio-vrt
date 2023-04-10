from pathlib import Path
from typing import Union
import xml.etree.cElementTree as ET
from xml.dom import minidom
from os.path import relpath

import rasterio as rio
from rasterio.enums import ColorInterp

def build_vrt(
    vrt_path: Union[str, Path],
    files: list[Union[str, Path]]
) -> Path:
    """Create a vrt file from multiple files

    Arguments:
        vrt_path: the final vrt file
        files: a list of rasterio readable files

    Returns:
        the path to the vrt file
    """

    # transform the final file in Path
    vrt_path = Path(vrt_path)

    # transform all the file path into Path objects
    files = [Path(f) for f in files]

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

    # extract transform from the "origin" tile i.e. the top-left corner
    # this avoids the final map to be completely offset
    for file in files:
        with rio.open(file) as f:
            if f.bounds.left == left and f.bounds.top == top:
                transform = f.transform

    total_width = round((right - left) / x_res)
    total_height = round((top - bottom) / y_res)

    # start the tree
    VRTDataset = ET.Element(
        'VRTDataset',
        {'rasterXSize': str(total_width),'rasterYSize': str(total_height)}
    )
    ET.SubElement(VRTDataset, 'SRS', {'dataAxisToSRSAxisMapping': '2,1'}).text = crs.wkt
    ET.SubElement(VRTDataset, "GeoTransform").text =", ".join([str(i) for i in transform.to_gdal()])
    ET.SubElement(VRTDataset, "overViewList", {"resampling": "nearest"}).text = "2 4 8"

    # create the bands subelements
    VRTRasterBands = {}
    for i in indexes:
        VRTRasterBands[i] = ET.SubElement(VRTDataset, "VRTRasterBand", {"datatype": dtypes[i-1], "band": str(i)})
        if colorinterps[i-1] != ColorInterp.undefined:
            ET.SubElement(VRTRasterBands[i], "ColorInterp").text = colorinterps[i-1].name.capitalize()

    # add the files
    for f in files:
        relativeToVRT = "0" if f.is_absolute() else "1"
        with rio.open(f) as src:
            for i in indexes:
                if colorinterps[i-1] == ColorInterp.alpha:
                    source_type = "ComplexSource"
                else:
                    source_type= "SimpleSource"

                Source = ET.SubElement(VRTRasterBands[i], source_type)
                ET.SubElement(Source, "SourceFilename", {"relativeToVRT": relativeToVRT}).text = str(f)
                ET.SubElement(Source, "SourceBand").text = str(i)
                ET.SubElement(Source, "SourceProperties", {
                    "RasterXSize": str(src.width),
                    "RasterYSize": str(src.height),
                    "DataType": str(dtypes[i-1]),
                    "BlockXSize": str(src.profile["blockxsize"]),
                    "BlockYSize": str(src.profile["blockysize"]),
                })
                ET.SubElement(Source, "SrcRect", {
                    "xOff":"0",
                    "yOff":"0",
                    "xSize": str(src.width),
                    "ySize": str(src.height),
                })
                ET.SubElement(Source, "DstRect", {
                    "xOff": str(abs(round((src.bounds.left - left)/x_res))),
                    "yOff": str(abs(round((src.bounds.top - top)/y_res))),
                    "xSize": str(src.width),
                    "ySize": str(src.height),
                })
                if nodatavals[i-1] is not None:
                    ET.SubElement(Source, "NoDataValue").text = str(nodatavals[i-1])
                ET.SubElement(Source, "Offset").text = "0.0"
                ET.SubElement(Source, "Scale").text = "1.0"

                if colorinterps[i-1] == ColorInterp.alpha:
                    ET.SubElement(Source, "UseMaskBand").text = "true"

    # write the file
    vrt_path.write_text(
        minidom.parseString(ET.tostring(VRTDataset).decode("utf-8"))
        .toprettyxml(indent="  ")
        .replace('&quot;', '"')
    )

    return vrt_path