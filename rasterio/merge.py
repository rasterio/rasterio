"""Copy valid pixels from input files to an output file."""

from contextlib import contextmanager
import logging
import math
from pathlib import Path
import warnings

import numpy as np

import rasterio
from rasterio.enums import Resampling
from rasterio import windows
from rasterio.transform import Affine


logger = logging.getLogger(__name__)

MERGE_METHODS = ('first', 'last', 'min', 'max')


def merge(
    datasets,
    bounds=None,
    res=None,
    nodata=None,
    dtype=None,
    precision=10,
    indexes=None,
    output_count=None,
    resampling=Resampling.nearest,
    method="first",
    dst_path=None,
    dst_kwds=None,
):
    """Copy valid pixels from input files to an output file.

    All files must have the same number of bands, data type, and
    coordinate reference system.

    Input files are merged in their listed order using the reverse
    painter's algorithm (default) or another method. If the output file exists,
    its values will be overwritten by input values.

    Geospatial bounds and resolution of a new output file in the
    units of the input file coordinate reference system may be provided
    and are otherwise taken from the first input file.

    Parameters
    ----------
    datasets : list of dataset objects opened in 'r' mode, filenames or pathlib.Path objects
        source datasets to be merged.
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
    dtype: numpy dtype or string
        dtype to use in outputfile. If not set, uses the dtype value in the
        first input raster.
    precision: float, optional
        Number of decimal points of precision when computing inverse transform.
    indexes : list of ints or a single int, optional
        bands to read and merge
    output_count: int, optional
        If using callable it may be useful to have additional bands in the output
        in addition to the indexes specified for read
    resampling : Resampling, optional
        Resampling algorithm used when reading input files.
        Default: `Resampling.nearest`.
    method : str or callable
        pre-defined method:
            first: reverse painting
            last: paint valid new on top of existing
            min: pixel-wise min of existing and new
            max: pixel-wise max of existing and new
        or custom callable with signature:

        def function(old_data, new_data, old_nodata, new_nodata, index=None, roff=None, coff=None):

            Parameters
            ----------
            old_data : array_like
                array to update with new_data
            new_data : array_like
                data to merge
                same shape as old_data
            old_nodata, new_data : array_like
                boolean masks where old/new data is nodata
                same shape as old_data
            index: int
                index of the current dataset within the merged dataset collection
            roff: int
                row offset in base array
            coff: int
                column offset in base array
    dst_path : str or Pathlike, optional
        Path of output dataset
    dst_kwds : dict, optional
        Dictionary of creation options and other paramters that will be
        overlaid on the profile of the output dataset.

    Returns
    -------
    tuple

        Two elements:

            dest: numpy ndarray
                Contents of all input rasters in single array

            out_transform: affine.Affine()
                Information for mapping pixel coordinates in `dest` to another
                coordinate system

    """
    if method not in MERGE_METHODS and not callable(method):
        raise ValueError('Unknown method {0}, must be one of {1} or callable'
                         .format(method, MERGE_METHODS))

    # Create a dataset_opener object to use in several places in this function.
    if isinstance(datasets[0], str) or isinstance(datasets[0], Path):
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

    logger.debug("Output bounds: %r", (dst_w, dst_s, dst_e, dst_n))
    output_transform = Affine.translation(dst_w, dst_n)
    logger.debug("Output transform, before scaling: %r", output_transform)

    # Resolution/pixel size
    if not res:
        res = first_res
    elif not np.iterable(res):
        res = (res, res)
    elif len(res) == 1:
        res = (res[0], res[0])
    output_transform *= Affine.scale(res[0], -res[1])
    logger.debug("Output transform, after scaling: %r", output_transform)

    # Compute output array shape. We guarantee it will cover the output
    # bounds completely
    output_width = int(math.ceil((dst_e - dst_w) / res[0]))
    output_height = int(math.ceil((dst_n - dst_s) / res[1]))

    # Adjust bounds to fit
    dst_e, dst_s = output_transform * (output_width, output_height)
    logger.debug("Output width: %d, height: %d", output_width, output_height)
    logger.debug("Adjusted bounds: %r", (dst_w, dst_s, dst_e, dst_n))

    if dtype is not None:
        dt = dtype
        logger.debug("Set dtype: %s", dt)

    out_profile = first_profile
    out_profile.update(**(dst_kwds or {}))

    out_profile["transform"] = output_transform
    out_profile["height"] = output_height
    out_profile["width"] = output_width
    out_profile["count"] = output_count
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
            info = np.finfo(dt)
            if np.isnan(nodataval):
                inrange = True
            else:
                inrange = (info.min <= nodataval <= info.max)
        if inrange:
            dest.fill(nodataval)
        else:
            warnings.warn(
                "Input file's nodata value, %s, is beyond the valid "
                "range of its data type, %s. Consider overriding it "
                "using the --nodata option for better results." % (
                    nodataval, dt))
    else:
        nodataval = 0

    if method == 'first':
        def copyto(old_data, new_data, old_nodata, new_nodata, **kwargs):
            mask = np.logical_and(old_nodata, ~new_nodata)
            old_data[mask] = new_data[mask]

    elif method == 'last':
        def copyto(old_data, new_data, old_nodata, new_nodata, **kwargs):
            mask = ~new_nodata
            old_data[mask] = new_data[mask]

    elif method == 'min':
        def copyto(old_data, new_data, old_nodata, new_nodata, **kwargs):
            mask = np.logical_and(~old_nodata, ~new_nodata)
            old_data[mask] = np.minimum(old_data[mask], new_data[mask])

            mask = np.logical_and(old_nodata, ~new_nodata)
            old_data[mask] = new_data[mask]

    elif method == 'max':
        def copyto(old_data, new_data, old_nodata, new_nodata, **kwargs):
            mask = np.logical_and(~old_nodata, ~new_nodata)
            old_data[mask] = np.maximum(old_data[mask], new_data[mask])

            mask = np.logical_and(old_nodata, ~new_nodata)
            old_data[mask] = new_data[mask]

    elif callable(method):
        copyto = method

    else:
        raise ValueError(method)

    for idx, dataset in enumerate(datasets):
        with dataset_opener(dataset) as src:
            # Real World (tm) use of boundless reads.
            # This approach uses the maximum amount of memory to solve the
            # problem. Making it more efficient is a TODO.

            # 1. Compute spatial intersection of destination and source
            src_w, src_s, src_e, src_n = src.bounds

            int_w = src_w if src_w > dst_w else dst_w
            int_s = src_s if src_s > dst_s else dst_s
            int_e = src_e if src_e < dst_e else dst_e
            int_n = src_n if src_n < dst_n else dst_n

            # 2. Compute the source window
            src_window = windows.from_bounds(
                int_w, int_s, int_e, int_n, src.transform, precision=precision
            )
            logger.debug("Src %s window: %r", src.name, src_window)

            src_window = src_window.round_shape()

            # 3. Compute the destination window
            dst_window = windows.from_bounds(
                int_w, int_s, int_e, int_n, output_transform, precision=precision
            )

            # 4. Read data in source window into temp
            trows, tcols = (int(round(dst_window.height)), int(round(dst_window.width)))
            temp_shape = (src_count, trows, tcols)
            temp = src.read(
                out_shape=temp_shape,
                window=src_window,
                boundless=False,
                masked=True,
                indexes=indexes,
                resampling=resampling,
            )

        # 5. Copy elements of temp into dest
        roff, coff = (
            int(round(dst_window.row_off)), int(round(dst_window.col_off)))

        region = dest[:, roff:roff + trows, coff:coff + tcols]
        if np.isnan(nodataval):
            region_nodata = np.isnan(region)
            temp_nodata = np.isnan(temp)
        else:
            region_nodata = region == nodataval
            temp_nodata = temp.mask

        copyto(region, temp, region_nodata, temp_nodata,
               index=idx, roff=roff, coff=coff)

    if dst_path is None:
        return dest, output_transform

    else:
        with rasterio.open(dst_path, "w", **out_profile) as dst:
            dst.write(dest)
            if first_colormap:
                dst.write_colormap(1, first_colormap)
