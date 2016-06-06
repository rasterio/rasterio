"""Copy valid pixels from input files to an output file."""

from __future__ import absolute_import

import logging
import math
import warnings

import numpy as np

from rasterio._base import get_window
from rasterio.transform import Affine

logger = logging.getLogger(__name__)


def merge(sources, bounds=None, res=None, nodata=None, precision=7):
    """Copy valid pixels from input files to an output file.

    All files must have the same number of bands, data type, and
    coordinate reference system.

    Input files are merged in their listed order using the reverse
    painter's algorithm. If the output file exists, its values will be
    overwritten by input values.

    Geospatial bounds and resolution of a new output file in the
    units of the input file coordinate reference system may be provided
    and are otherwise taken from the first input file.

    Parameters
    ----------
    sources: list of source datasets
        Open rasterio RasterReader objects to be merged.
    bounds: tuple, optional
        Bounds of the output image (left, bottom, right, top).
        If not set, bounds are determined from bounds of input rasters.
    res: tuple, optional
        Output resolution in units of coordinate reference system. If not set,
        the resolution of the first raster is used. If a single value is passed,
        output pixels will be square.
    nodata: float, optional
        nodata value to use in output file. If not set, uses the nodata value
        in the first input raster.

    Returns
    -------
    dest: numpy ndarray
        Contents of all input rasters in single array.
    out_transform: affine object
        Information for mapping pixel coordinates in `dest` to another
        coordinate system
    """
    first = sources[0]
    first_res = first.res
    nodataval = first.nodatavals[0]
    dtype = first.dtypes[0]

    # Extent from option or extent of all inputs.
    if bounds:
        dst_w, dst_s, dst_e, dst_n = bounds
    else:
        # scan input files.
        xs = []
        ys = []
        for src in sources:
            left, bottom, right, top = src.bounds
            xs.extend([left, right])
            ys.extend([bottom, top])
        dst_w, dst_s, dst_e, dst_n = min(xs), min(ys), max(xs), max(ys)

    logger.debug("Output bounds: %r", (dst_w, dst_s, dst_e, dst_n))
    output_transform = Affine.translation(dst_w, dst_n)
    logger.debug("Output transform, before scaling: %r", output_transform)

    # Resolution/pixel size.
    if not res:
        res = first_res
    elif not np.iterable(res):
        res = (res, res)
    elif len(res) == 1:
        res = (res[0], res[0])
    output_transform *= Affine.scale(res[0], -res[1])
    logger.debug("Output transform, after scaling: %r", output_transform)

    # Compute output array shape. We guarantee it will cover the output
    # bounds completely.
    output_width = int(math.ceil((dst_e - dst_w) / res[0]))
    output_height = int(math.ceil((dst_n - dst_s) / res[1]))

    # Adjust bounds to fit.
    dst_e, dst_s = output_transform * (output_width, output_height)
    logger.debug("Output width: %d, height: %d", output_width, output_height)
    logger.debug("Adjusted bounds: %r", (dst_w, dst_s, dst_e, dst_n))

    # create destination array
    dest = np.zeros((first.count, output_height, output_width), dtype=dtype)

    if nodata is not None:
        nodataval = nodata
        logger.debug("Set nodataval: %r", nodataval)

    if nodataval is not None:
        # Only fill if the nodataval is within dtype's range.
        inrange = False
        if np.dtype(dtype).kind in ('i', 'u'):
            info = np.iinfo(dtype)
            inrange = (info.min <= nodataval <= info.max)
        elif np.dtype(dtype).kind == 'f':
            info = np.finfo(dtype)
            inrange = (info.min <= nodataval <= info.max)
        if inrange:
            dest.fill(nodataval)
        else:
            warnings.warn(
                "Input file's nodata value, %s, is beyond the valid "
                "range of its data type, %s. Consider overriding it "
                "using the --nodata option for better results." % (
                    nodataval, dtype))
    else:
        nodataval = 0

    for src in sources:
        # Real World (tm) use of boundless reads.
        # This approach uses the maximum amount of memory to solve the problem.
        # Making it more efficient is a TODO.

        # 1. Compute spatial intersection of destination and source.
        src_w, src_s, src_e, src_n = src.bounds

        int_w = src_w if src_w > dst_w else dst_w
        int_s = src_s if src_s > dst_s else dst_s
        int_e = src_e if src_e < dst_e else dst_e
        int_n = src_n if src_n < dst_n else dst_n

        # 2. Compute the source window.
        src_window = get_window(
            int_w, int_s, int_e, int_n, src.affine, precision=precision)
        logger.debug("Src %s window: %r", src.name, src_window)

        # 3. Compute the destination window.
        dst_window = get_window(
            int_w, int_s, int_e, int_n, output_transform, precision=precision)
        logger.debug("Dst window: %r", dst_window)

        # 4. Initialize temp array.
        tcount = first.count
        trows, tcols = tuple(b - a for a, b in dst_window)

        temp_shape = (tcount, trows, tcols)
        logger.debug("Temp shape: %r", temp_shape)

        temp = np.zeros(temp_shape, dtype=dtype)
        temp = src.read(out=temp, window=src_window, boundless=False,
                        masked=True)

        # 5. Copy elements of temp into dest.
        roff, coff = dst_window[0][0], dst_window[1][0]

        region = dest[:, roff:roff + trows, coff:coff + tcols]
        np.copyto(
            region, temp,
            where=np.logical_and(region == nodataval, temp.mask == False))

    return dest, output_transform
