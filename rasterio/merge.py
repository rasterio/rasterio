"""Copy valid pixels from input files to an output file."""

from contextlib import contextmanager
import logging
import os
import math
import warnings
from xml.etree import ElementTree as ET

import numpy as np

import rasterio
from rasterio.coords import disjoint_bounds
from rasterio.dtypes import _gdal_typename
from rasterio.enums import MaskFlags
from rasterio.enums import Resampling
from rasterio.errors import RasterioDeprecationWarning, RasterioError
from rasterio import windows
from rasterio._path import _parse_path
from rasterio.transform import Affine

logger = logging.getLogger(__name__)


def copy_first(merged_data, new_data, merged_mask, new_mask, **kwargs):
    """Returns the first available pixel."""
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_last(merged_data, new_data, merged_mask, new_mask, **kwargs):
    """Returns the last available pixel."""
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_not(new_mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_min(merged_data, new_data, merged_mask, new_mask, **kwargs):
    """Returns the minimum value pixel."""
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.minimum(merged_data, new_data, out=merged_data, where=mask, casting="unsafe")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_max(merged_data, new_data, merged_mask, new_mask, **kwargs):
    """Returns the maximum value pixel."""
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.maximum(merged_data, new_data, out=merged_data, where=mask, casting="unsafe")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_sum(merged_data, new_data, merged_mask, new_mask, **kwargs):
    """Returns the sum of all pixel values."""
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.add(merged_data, new_data, out=merged_data, where=mask, casting="unsafe")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_count(merged_data, new_data, merged_mask, new_mask, **kwargs):
    """Returns the count of valid pixels."""
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.add(merged_data, mask, out=merged_data, where=mask, casting="unsafe")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, mask, where=mask, casting="unsafe")


MERGE_METHODS = {
    "first": copy_first,
    "last": copy_last,
    "min": copy_min,
    "max": copy_max,
    "sum": copy_sum,
    "count": copy_count,
}


def merge(
    datasets,
    bounds=None,
    res=None,
    nodata=None,
    dtype=None,
    precision=None,
    indexes=None,
    output_count=None,
    resampling=Resampling.nearest,
    method="first",
    target_aligned_pixels=False,
    dst_path=None,
    dst_kwds=None,
):
    """Copy valid pixels from input files to an output file.

    All files must have the same number of bands, data type, and
    coordinate reference system.

    Input files are merged in their listed order using the reverse
    painter's algorithm (default) or another method. If the output file
    exists, its values will be overwritten by input values.

    Geospatial bounds and resolution of a new output file in the units
    of the input file coordinate reference system may be provided and
    are otherwise taken from the first input file.

    Parameters
    ----------
    datasets : list
        List of dataset objects opened in 'r' mode, filenames or
        PathLike objects source datasets to be merged.
    bounds: tuple, optional
        Bounds of the output image (left, bottom, right, top).  If not
        set, bounds are determined from bounds of input rasters.
    res: tuple, optional
        Output resolution in units of coordinate reference system. If
        not set, the resolution of the first raster is used. If a single
        value is passed, output pixels will be square.
    nodata: float, optional
        Nodata value to use in output file. If not set, uses the nodata
        value in the first input raster.
    dtype: numpy.dtype or string
        Data type to use in outputfile. If not set, uses the dtype value
        in the first input raster.
    precision: int, optional
        This parameters is unused, deprecated in rasterio 1.3.0, and
        will be removed in version 2.0.0.
    indexes : list of ints or a single int, optional
        Bands to read and merge
    output_count: int, optional
        If using callable it may be useful to have additional bands in
        the output in addition to the indexes specified for read
    resampling : Resampling, optional
        Resampling algorithm used when reading input files.  Default:
        `Resampling.nearest`.
    method : str or callable
        pre-defined method:
            first: reverse painting
            last: paint valid new on top of existing
            min: pixel-wise min of existing and new
            max: pixel-wise max of existing and new
        or custom callable with signature:
            merged_data : array_like
                Array to update with new_data
            new_data : array_like
                Data to merge
                same shape as merged_data
            merged_mask, new_mask : array_like
                Boolean masks where merged/new data pixels are invalid
                same shape as merged_data
            index: int
                Index of the current dataset within the merged dataset
                collection
            roff: int
                Row offset in base array
            coff: int
                Column offset in base array

    target_aligned_pixels : bool, optional
        Whether to adjust output image bounds so that pixel coordinates
        are integer multiples of pixel size, matching the ``-tap``
        options of GDAL utilities.  Default: False.
    dst_path : str or PathLike, optional
        Path of output dataset
    dst_kwds : dict, optional
        Dictionary of creation options and other paramters that will be
        overlaid on the profile of the output dataset.

    Returns
    -------
    tuple

        Two elements:

            dest: numpy.ndarray
                Contents of all input rasters in single array

            out_transform: affine.Affine()
                Information for mapping pixel coordinates in `dest` to
                another coordinate system

    """
    if precision is not None:
        warnings.warn(
            "The precision parameter is unused, deprecated, and will be removed in 2.0.0.",
            RasterioDeprecationWarning,
        )

    if method in MERGE_METHODS:
        copyto = MERGE_METHODS[method]
    elif callable(method):
        copyto = method
    else:
        raise ValueError('Unknown method {0}, must be one of {1} or callable'
                         .format(method, list(MERGE_METHODS.keys())))

    # Create a dataset_opener object to use in several places in this function.
    if isinstance(datasets[0], (str, os.PathLike)):
        dataset_opener = rasterio.open
    else:

        @contextmanager
        def nullcontext(obj):
            try:
                yield obj
            finally:
                pass

        dataset_opener = nullcontext

    with dataset_opener(datasets[0]) as first:
        first_profile = first.profile
        first_crs = first.crs
        first_res = first.res
        nodataval = first.nodatavals[0]
        dt = first.dtypes[0]

        if indexes is None:
            src_count = first.count
        elif isinstance(indexes, int):
            src_count = indexes
        else:
            src_count = len(indexes)

        try:
            first_colormap = first.colormap(1)
        except ValueError:
            first_colormap = None

    if not output_count:
        output_count = src_count

    # Extent from option or extent of all inputs
    if bounds:
        dst_w, dst_s, dst_e, dst_n = bounds
    else:
        # scan input files
        xs = []
        ys = []
        for dataset in datasets:
            with dataset_opener(dataset) as src:
                left, bottom, right, top = src.bounds
            xs.extend([left, right])
            ys.extend([bottom, top])
        dst_w, dst_s, dst_e, dst_n = min(xs), min(ys), max(xs), max(ys)

    # Resolution/pixel size
    if not res:
        res = first_res
    elif not np.iterable(res):
        res = (res, res)
    elif len(res) == 1:
        res = (res[0], res[0])

    if target_aligned_pixels:
        dst_w = math.floor(dst_w / res[0]) * res[0]
        dst_e = math.ceil(dst_e / res[0]) * res[0]
        dst_s = math.floor(dst_s / res[1]) * res[1]
        dst_n = math.ceil(dst_n / res[1]) * res[1]

    # Compute output array shape. We guarantee it will cover the output
    # bounds completely
    output_width = int(round((dst_e - dst_w) / res[0]))
    output_height = int(round((dst_n - dst_s) / res[1]))

    output_transform = Affine.translation(dst_w, dst_n) * Affine.scale(res[0], -res[1])

    if dtype is not None:
        dt = dtype
        logger.debug("Set dtype: %s", dt)

    out_profile = first_profile
    out_profile.update(**(dst_kwds or {}))

    out_profile["transform"] = output_transform
    out_profile["height"] = output_height
    out_profile["width"] = output_width
    out_profile["count"] = output_count
    out_profile["dtype"] = dt
    if nodata is not None:
        out_profile["nodata"] = nodata

    # create destination array
    dest = np.zeros((output_count, output_height, output_width), dtype=dt)

    if nodata is not None:
        nodataval = nodata
        logger.debug("Set nodataval: %r", nodataval)

    if nodataval is not None:
        # Only fill if the nodataval is within dtype's range
        inrange = False
        if np.issubdtype(dt, np.integer):
            info = np.iinfo(dt)
            inrange = (info.min <= nodataval <= info.max)
        elif np.issubdtype(dt, np.floating):
            if math.isnan(nodataval):
                inrange = True
            else:
                info = np.finfo(dt)
                inrange = (info.min <= nodataval <= info.max)
        if inrange:
            dest.fill(nodataval)
        else:
            warnings.warn(
                "The nodata value, %s, is beyond the valid "
                "range of the chosen data type, %s. Consider overriding it "
                "using the --nodata option for better results." % (
                    nodataval, dt))
    else:
        nodataval = 0

    for idx, dataset in enumerate(datasets):
        with dataset_opener(dataset) as src:
            # Real World (tm) use of boundless reads.
            # This approach uses the maximum amount of memory to solve the
            # problem. Making it more efficient is a TODO.

            # 0. Precondition checks
            #    - Check that source is within destination bounds
            #    - Check that CRS is same

            if disjoint_bounds((dst_w, dst_s, dst_e, dst_n), src.bounds):
                logger.debug(
                    "Skipping source: src=%r, bounds=%r",
                    src,
                    (dst_w, dst_s, dst_e, dst_n),
                )
                continue

            if first_crs != src.crs:
                raise RasterioError(f"CRS mismatch with source: {dataset}")

            # 1. Compute spatial intersection of destination and source
            src_w, src_s, src_e, src_n = src.bounds

            int_w = src_w if src_w > dst_w else dst_w
            int_s = src_s if src_s > dst_s else dst_s
            int_e = src_e if src_e < dst_e else dst_e
            int_n = src_n if src_n < dst_n else dst_n

            # 2. Compute the source window
            src_window = windows.from_bounds(int_w, int_s, int_e, int_n, src.transform)

            # 3. Compute the destination window
            dst_window = windows.from_bounds(
                int_w, int_s, int_e, int_n, output_transform
            )

            # 4. Read data in source window into temp
            src_window_rnd_shp = src_window.round_lengths()
            dst_window_rnd_shp = dst_window.round_lengths()
            dst_window_rnd_off = dst_window_rnd_shp.round_offsets()

            temp_height, temp_width = (
                dst_window_rnd_off.height,
                dst_window_rnd_off.width,
            )
            temp_shape = (src_count, temp_height, temp_width)

            temp_src = src.read(
                out_shape=temp_shape,
                window=src_window_rnd_shp,
                boundless=False,
                masked=True,
                indexes=indexes,
                resampling=resampling,
            )

        # 5. Copy elements of temp into dest
        roff, coff = (
            max(0, dst_window_rnd_off.row_off),
            max(0, dst_window_rnd_off.col_off),
        )
        region = dest[:, roff : roff + temp_height, coff : coff + temp_width]

        if math.isnan(nodataval):
            region_mask = np.isnan(region)
        elif np.issubdtype(region.dtype, np.floating):
            region_mask = np.isclose(region, nodataval)
        else:
            region_mask = region == nodataval

        # Ensure common shape, resolving issue #2202.
        temp = temp_src[:, : region.shape[1], : region.shape[2]]
        temp_mask = np.ma.getmask(temp)
        copyto(region, temp, region_mask, temp_mask, index=idx, roff=roff, coff=coff)

    if dst_path is None:
        return dest, output_transform

    else:
        with rasterio.open(dst_path, "w", **out_profile) as dst:
            dst.write(dest)
            if first_colormap:
                dst.write_colormap(1, first_colormap)


def virtual_merge(
    datasets,
    bounds=None,
    res=None,
    nodata=None,
    background=None,
    hidenodata=False,
    dtype=None,
    indexes=None,
    output_count=None,
    resampling=Resampling.nearest,
    target_aligned_pixels=False,
    dst_path=None,
    dst_kwds=None,
) -> str:
    """Merge multiple datasets into a single virtual dataset.

    All files must have the same number of bands, data type, and
    coordinate reference system.

    Input files are merged in their listed order using the reverse
    painter's algorithm (default) or another method. If the output file
    exists, its values will be overwritten by input values.

    Geospatial bounds and resolution of a new output file in the units
    of the input file coordinate reference system may be provided and
    are otherwise taken from the first input file.

    Roughly equivalent to GDAL's GDALBuildVrt utility.

    Parameters
    ----------
    datasets : list
        List of dataset objects opened in 'r' mode, filenames or
        PathLike objects source datasets to be merged.
    bounds: tuple, optional
        Bounds of the output image (left, bottom, right, top).  If not
        set, bounds are determined from bounds of input rasters.
    res: tuple, optional
        Output resolution in units of coordinate reference system. If
        not set, the resolution of the first raster is used. If a single
        value is passed, output pixels will be square.
    nodata: float, optional
        Nodata value to use in output file. If not set, uses the nodata
        value in the first input raster.
    background : int or float, optional
        The background fill value for the VRT.
    dtype: numpy.dtype or string
        Data type to use in outputfile. If not set, uses the dtype value
        in the first input raster.
    indexes : list of ints or a single int, optional
        Bands to read and merge
    output_count: int, optional
        If using callable it may be useful to have additional bands in
        the output in addition to the indexes specified for read
    resampling : Resampling, optional
        Resampling algorithm used when reading input files.  Default:
        `Resampling.nearest`.
    target_aligned_pixels : bool, optional
        Whether to adjust output image bounds so that pixel coordinates
        are integer multiples of pixel size, matching the ``-tap``
        options of GDAL utilities.  Default: False.
    dst_path : str or PathLike, optional
        Path of output dataset
    dst_kwds : dict, optional
        Dictionary of creation options and other paramters that will be
        overlaid on the profile of the output dataset.

    Returns
    -------
    str
        XML text describing the virtual dataset (VRT).

    Notes
    -----
    The methods of the original merge function could be replaced here
    by C pixel functions. A TODO?

    """
    if isinstance(datasets[0], (str, os.PathLike)):
        dataset_opener = rasterio.open
    else:

        @contextmanager
        def nullcontext(obj):
            try:
                yield obj
            finally:
                pass

        dataset_opener = nullcontext

    with dataset_opener(datasets[0]) as first:
        first_res = first.res
        nodataval = first.nodatavals[0]
        crs_wkt = first.crs.wkt
        indexes = first.indexes
        colorinterps = first.colorinterp
        block_shapes = first.block_shapes
        dtypes = first.dtypes
        mask_flag_enums = first.mask_flag_enums
        dt = dtypes[0]

        if indexes is None:
            src_count = first.count
        elif isinstance(indexes, int):
            src_count = indexes
        else:
            src_count = len(indexes)

    if not output_count:
        output_count = src_count

    # Extent from option or extent of all inputs
    if bounds:
        dst_w, dst_s, dst_e, dst_n = bounds
    else:
        # scan input files
        xs = []
        ys = []
        for dataset in datasets:
            with dataset_opener(dataset) as src:
                left, bottom, right, top = src.bounds
            xs.extend([left, right])
            ys.extend([bottom, top])
        dst_w, dst_s, dst_e, dst_n = min(xs), min(ys), max(xs), max(ys)

    # Resolution/pixel size
    if not res:
        res = first_res
    elif not np.iterable(res):
        res = (res, res)
    elif len(res) == 1:
        res = (res[0], res[0])

    if target_aligned_pixels:
        dst_w = math.floor(dst_w / res[0]) * res[0]
        dst_e = math.ceil(dst_e / res[0]) * res[0]
        dst_s = math.floor(dst_s / res[1]) * res[1]
        dst_n = math.ceil(dst_n / res[1]) * res[1]

    # Compute output shape. We guarantee it will cover the output bounds
    # completely.
    output_width = int(round((dst_e - dst_w) / res[0]))
    output_height = int(round((dst_n - dst_s) / res[1]))

    output_transform = Affine.translation(dst_w, dst_n) * Affine.scale(res[0], -res[1])

    if dtype is not None:
        dt = dtype
        logger.debug("Set dtype: %s", dt)

    # create destination array
    # dest = np.zeros((output_count, output_height, output_width), dtype=dt)

    # Create destination VRT.
    vrtdataset = ET.Element(
        "VRTDataset",
        rasterYSize=str(output_height),
        rasterXSize=str(output_width),
    )

    ET.SubElement(vrtdataset, "SRS").text = crs_wkt if crs_wkt else ""
    ET.SubElement(vrtdataset, "GeoTransform").text = ",".join(
        [str(v) for v in output_transform.to_gdal()]
    )

    if nodata is not None:
        # Only fill if the nodataval is within dtype's range
        inrange = False
        if np.issubdtype(dt, np.integer):
            info = np.iinfo(dt)
            inrange = info.min <= nodata <= info.max
        elif np.issubdtype(dt, np.floating):
            if math.isnan(nodata):
                inrange = True
            else:
                info = np.finfo(dt)
                inrange = info.min <= nodata <= info.max
        if inrange:
            nodataval = nodata
        else:
            warnings.warn(
                "The nodata value, %s, is beyond the valid "
                "range of the chosen data type, %s. Consider overriding it "
                "using the --nodata option for better results." % (nodataval, dt)
            )
    else:
        nodataval = None

    # Create VRT bands.
    for bidx, ci, block_shape, dtype in zip(
        indexes, colorinterps, block_shapes, dtypes
    ):
        vrtrasterband = ET.SubElement(
            vrtdataset,
            "VRTRasterBand",
            dataType=_gdal_typename(dtype),
            band=str(bidx),
        )

        if background is not None or nodataval is not None:
            ET.SubElement(vrtrasterband, "NoDataValue").text = str(
                background or nodataval
            )

            if hidenodata:
                ET.SubElement(vrtrasterband, "HideNoDataValue").text = "1"

        ET.SubElement(vrtrasterband, "ColorInterp").text = ci.name.capitalize()

    # Add sources to VRT bands.
    for idx, dataset in enumerate(datasets):
        with dataset_opener(dataset) as src:
            for bidx, ci, block_shape, dtype in zip(
                src.indexes, src.colorinterp, src.block_shapes, src.dtypes
            ):
                vrtrasterband = vrtdataset.find(f"VRTRasterBand[@band='{bidx}']")
                complexsource = ET.SubElement(
                    vrtrasterband, "ComplexSource", resampling=resampling.name
                )
                ET.SubElement(
                    complexsource, "SourceFilename", relativeToVRT="0", shared="0"
                ).text = _parse_path(src.name).as_vsi()
                ET.SubElement(complexsource, "SourceBand").text = str(bidx)
                ET.SubElement(
                    complexsource,
                    "SourceProperties",
                    RasterXSize=str(output_width),
                    RasterYSize=str(output_height),
                    dataType=_gdal_typename(dtype),
                    BlockYSize=str(block_shape[0]),
                    BlockXSize=str(block_shape[1]),
                )
                ET.SubElement(
                    complexsource,
                    "SrcRect",
                    xOff="0",
                    yOff="0",
                    xSize=str(src.width),
                    ySize=str(src.height),
                )
                ET.SubElement(
                    complexsource,
                    "DstRect",
                    xOff=str(
                        (src.transform.xoff - output_transform.xoff)
                        / output_transform.a
                    ),
                    yOff=str(
                        (src.transform.yoff - output_transform.yoff)
                        / output_transform.e
                    ),
                    xSize=str(src.width * src.transform.a / output_transform.a),
                    ySize=str(src.height * src.transform.e / output_transform.e),
                )

                if src.nodata is not None:
                    ET.SubElement(complexsource, "NODATA").text = str(src.nodata)

                if src.options is not None:
                    openoptions = ET.SubElement(complexsource, "OpenOptions")
                    for ookey, oovalue in src.options.items():
                        ET.SubElement(openoptions, "OOI", key=str(ookey)).text = str(
                            oovalue
                        )

    if all(MaskFlags.per_dataset in flags for flags in mask_flag_enums):
        maskband = ET.SubElement(vrtdataset, "MaskBand")
        vrtrasterband = ET.SubElement(maskband, "VRTRasterBand", dataType="Byte")

        for idx, dataset in enumerate(datasets):
            with dataset_opener(dataset) as src:
                for bidx, ci, block_shape, dtype in zip(
                    src.indexes, src.colorinterp, src.block_shapes, src.dtypes
                ):
                    simplesource = ET.SubElement(
                        vrtrasterband, "SimpleSource", resampling=resampling.name
                    )
                    ET.SubElement(
                        simplesource, "SourceFilename", relativeToVRT="0", shared="0"
                    ).text = _parse_path(src.name).as_vsi()
                    ET.SubElement(simplesource, "SourceBand").text = "mask,1"
                    ET.SubElement(
                        simplesource,
                        "SourceProperties",
                        RasterXSize=str(output_width),
                        RasterYSize=str(output_height),
                        dataType="Byte",
                        BlockYSize=str(block_shape[0]),
                        BlockXSize=str(block_shape[1]),
                    )
                    ET.SubElement(
                        simplesource,
                        "SrcRect",
                        xOff="0",
                        yOff="0",
                        xSize=str(src.width),
                        ySize=str(src.height),
                    )
                    ET.SubElement(
                        simplesource,
                        "DstRect",
                        xOff=str(
                            (src.transform.xoff - output_transform.xoff)
                            / output_transform.a
                        ),
                        yOff=str(
                            (src.transform.yoff - output_transform.yoff)
                            / output_transform.e
                        ),
                        xSize=str(src.width * src.transform.a / output_transform.a),
                        ySize=str(src.height * src.transform.e / output_transform.e),
                    )

    return ET.tostring(vrtdataset, encoding="utf-8")
