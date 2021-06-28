"""Copy valid pixels from input files to an output file."""

from contextlib import contextmanager
from collections.abc import Sequence
from functools import reduce
from operator import mul
import logging
import math
from pathlib import Path
import warnings

import numpy as np

import rasterio._loading

with rasterio._loading.add_gdal_dll_directories():
    import rasterio
    from rasterio.coords import BoundingBox, disjoint_bounds
    from rasterio.enums import Resampling
    from rasterio import windows
    from rasterio.transform import Affine
    from rasterio.errors import WindowError


logger = logging.getLogger(__name__)


def copy_first(merged_data, new_data, merged_mask, new_mask, **kwargs):
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_last(merged_data, new_data, merged_mask, new_mask, **kwargs):
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_not(new_mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_min(merged_data, new_data, merged_mask, new_mask, **kwargs):
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.minimum(merged_data, new_data, out=merged_data, where=mask)
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


def copy_max(merged_data, new_data, merged_mask, new_mask, **kwargs):
    mask = np.empty_like(merged_mask, dtype="bool")
    np.logical_or(merged_mask, new_mask, out=mask)
    np.logical_not(mask, out=mask)
    np.maximum(merged_data, new_data, out=merged_data, where=mask)
    np.logical_not(new_mask, out=mask)
    np.logical_and(merged_mask, mask, out=mask)
    np.copyto(merged_data, new_data, where=mask, casting="unsafe")


MERGE_METHODS = {
    'first': copy_first,
    'last': copy_last,
    'min': copy_min,
    'max': copy_max
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

        def function(merged_data, new_data, merged_mask, new_mask, index=None, roff=None, coff=None):

            Parameters
            ----------
            merged_data : array_like
                array to update with new_data
            new_data : array_like
                data to merge
                same shape as merged_data
            merged_mask, new_mask : array_like
                boolean masks where merged/new data pixels are invalid
                same shape as merged_data
            index: int
                index of the current dataset within the merged dataset collection
            roff: int
                row offset in base array
            coff: int
                column offset in base array

    target_aligned_pixels : bool, optional
        Whether to adjust output image bounds so that pixel coordinates
        are integer multiples of pixel size, matching the ``-tap``
        options of GDAL utilities.  Default: False.
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
    if method in MERGE_METHODS:
        copyto = MERGE_METHODS[method]
    elif callable(method):
        copyto = method
    else:
        raise ValueError('Unknown method {0}, must be one of {1} or callable'
                         .format(method, list(MERGE_METHODS.keys())))

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

            if disjoint_bounds((dst_w, dst_s, dst_e, dst_n), src.bounds):
                logger.debug("Skipping source: src=%r, window=%r", src)
                continue

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

            # 3. Compute the destination window
            dst_window = windows.from_bounds(
                int_w, int_s, int_e, int_n, output_transform, precision=precision
            )

            # 4. Read data in source window into temp
            src_window_rnd_shp = src_window.round_shape(pixel_precision=0)
            dst_window_rnd_shp = dst_window.round_shape(pixel_precision=0)
            dst_window_rnd_off = dst_window_rnd_shp.round_offsets(pixel_precision=0)
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


def arrbytes(shape, dtype):
    return reduce(mul, shape) * np.dtype(dtype).itemsize


def arrblocks(shape, dtype, mem_limit=1024*1024):
    i = 1
    new_shape = [shape[0], shape[1]//i, shape[2]//i]
    while arrbytes(new_shape, dtype) >= mem_limit:
        i += 1
        new_shape[1] = shape[1] // i
        new_shape[2] = shape[2] // i
    return tuple(new_shape), _gen_blocks(shape, new_shape)

def arrblocksxy(shape, width, height):
    return _gen_blocks(shape, (shape[0], height, width))

def _gen_blocks(shape, block_shape):
    blocks = []
    row_blocks = divmod(shape[1], block_shape[1])
    col_blocks = divmod(shape[2], block_shape[2])
    #breakpoint()
    for j in range(row_blocks[0] + (row_blocks[1] > 0)): # rows
        for k in range(col_blocks[0] + (col_blocks[1] > 0)):  # cols
            h, w = block_shape[1:]
            col_off = w * k
            row_off = h * j

            if col_off < shape[2] and col_off + w > shape[2]:
                w = shape[2] % w
            if row_off < shape[1] and row_off + h > shape[1]:
                h = shape[1] % h
            blocks.append(windows.Window(col_off, row_off, w, h))
    return blocks


def dataset_opener(dataset):
    if isinstance(dataset, (str, Path)):
        fin = rasterio.open(dataset)
        return fin
    else:
        return dataset


def merge_tiled(
    datasets,
    dst_path,
    bounds=None,
    res=None,
    nodata=None,
    dtype=None,
    indexes=None,
    output_count=None,
    resampling=Resampling.nearest,
    method="first",
    target_aligned_pixels=False,
    dst_kwds=None,
    memory_limit=None,
    block_shape=None
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

        def function(merged_data, new_data, merged_mask, new_mask, index=None, roff=None, coff=None):

            Parameters
            ----------
            merged_data : array_like
                array to update with new_data
            new_data : array_like
                data to merge
                same shape as merged_data
            merged_mask, new_mask : array_like
                boolean masks where merged/new data pixels are invalid
                same shape as merged_data
            index: int
                index of the current dataset within the merged dataset collection
            roff: int
                row offset in base array
            coff: int
                column offset in base array

    target_aligned_pixels : bool, optional
        Whether to adjust output image bounds so that pixel coordinates
        are integer multiples of pixel size, matching the ``-tap``
        options of GDAL utilities.  Default: False.
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
    if method in MERGE_METHODS:
        copyto = MERGE_METHODS[method]
    elif callable(method):
        copyto = method
    else:
        raise ValueError('Unknown method {0}, must be one of {1} or callable'
                         .format(method, list(MERGE_METHODS.keys())))

    DS = tuple(map(dataset_opener, datasets))
    nodataval = DS[0].nodatavals[0]
    dt = DS[0].dtypes[0]

    if indexes is None:
        src_count = DS[0].count
    elif isinstance(indexes, int):
        src_count = indexes
    else:
        src_count = len(indexes)

    # Compute destination bounds
    if bounds:
        dst_w, dst_s, dst_e, dst_n = bounds
    else:
        dst_w, dst_s, dst_e, dst_n = (np.inf, np.inf, -np.inf, -np.inf)
        for src in DS:
            dst_w = min(src.bounds[0], dst_w)
            dst_s = min(src.bounds[1], dst_s)
            dst_e = max(src.bounds[2], dst_e)
            dst_n = max(src.bounds[3], dst_n)

    # Compute destination resolution
    if not res:
        res = min(src.res for src in DS)
    elif isinstance(res, (float, int)):
        res = (res, res)
    elif isinstance(res, Sequence) and len(res) == 1:
        res = (res[0], res[0])

    if dtype is not None:
        dt = dtype
        logger.debug("Set dtype: %s", dt)
    
    if nodata is not None:
        nodataval = nodata
        logger.debug("Set nodataval: %r", nodataval)

    inrange = False
    if nodataval is not None:
        # Only fill if the nodataval is within dtype's range
        if np.issubdtype(dt, np.integer):
            info = np.iinfo(dt)
            inrange = (info.min <= nodataval <= info.max)
        elif np.issubdtype(dt, np.floating):
            if math.isnan(nodataval):
                inrange = True
            else:
                info = np.finfo(dt)
                inrange = (info.min <= nodataval <= info.max)
        if not inrange:
            warnings.warn(
                "The nodata value, %s, is beyond the valid "
                "range of the chosen data type, %s. Consider overriding it "
                "using the --nodata option for better results." % (
                    nodataval, dt))
    else:
        nodataval = 0


    if target_aligned_pixels:
        dst_w = math.floor(dst_w / res[0]) * res[0]
        dst_e = math.ceil(dst_e / res[0]) * res[0]
        dst_s = math.floor(dst_s / res[1]) * res[1]
        dst_n = math.ceil(dst_n / res[1]) * res[1]

    # Compute output array shape. We guarantee it will cover the output
    # bounds completely
    if not output_count:
        output_count = src_count
    output_width = round((dst_e - dst_w) / res[0])
    output_height = round((dst_n - dst_s) / res[1])
    output_transform = Affine.translation(dst_w, dst_n) * Affine.scale(res[0], -res[1])

    out_profile = dict(DS[0].profile)
    out_profile.update(**(dst_kwds or {}))
    out_profile['transform'] = output_transform
    out_profile['height'] = output_height
    out_profile['width'] = output_width
    out_profile['count'] = output_count
    if nodata is not None:
        out_profile['nodata'] = nodata

    dest_shape = (output_count, output_height, output_width)
    if memory_limit is not None and block_shape is not None:
        raise ValueError("Can only set memory limit or block_shape, but not both")
    if memory_limit:
        block_shape, blocks = arrblocks(dest_shape, dt, mem_limit=memory_limit)
    elif block_shape:
        assert len(block_shape) == 2
        blocks = arrblocksxy(dest_shape, *block_shape)
    else:
        block_shape, blocks = arrblocks(dest_shape, dt, mem_limit=1024*1024*256)
    
    with rasterio.open(dst_path, 'w', **out_profile) as dest:
        for i, block in enumerate(blocks):
            tile = np.zeros((output_count, block.height, block.width), dtype=dt)
            if inrange:
                tile.fill(nodataval)
            
            tile_bounds = windows.bounds(block, output_transform)
            tile_transform = windows.transform(block, output_transform)
            for idx, ds in enumerate(DS):
                # Intersect source bounds and tile bounds
                try:
                    ibounds = intersect_bounds(ds.bounds, tile_bounds, tile_transform)
                    sw = wfrombounds(ibounds, ds.transform)
                    dw = wfrombounds(ibounds, tile_transform)
                except (ValueError, WindowError):
                    continue

                rows, cols = dw.toslices()
                new_data = np.ma.masked_all_like(tile)
                data = ds.read(
                    out_shape=(output_count, *windows.shape(dw)),
                    indexes=indexes,
                    masked=True,
                    boundless=False,
                    window=sw,
                    resampling=resampling
                )
                new_data[:, rows, cols] = data

                copyto(tile, new_data, tile==nodataval, new_data.mask, index=idx, roff=dw.row_off, coff=dw.col_off)
            dest.write(tile, window=block)
        try:
            cmap = DS[0].colormap(1)
            dest.write_colormap(1, cmap)
        except ValueError:
            pass

    for ds in DS:
        ds.close()

def wfrombounds(bounds, transform):
    # Based on gdal_merge.py
    ulx = bounds[0]
    uly = bounds[3]
    lrx = bounds[2]
    lry = bounds[1]

    xoff = int((ulx - transform.c) / transform.a + 0.1)
    yoff = int((uly - transform.f) / transform.e + 0.1)
    width = round((lrx - transform.c) / transform.a) - xoff
    height = round((lry - transform.f) / transform.e) - yoff
    if width < 1 or height < 1:
        raise WindowError
    return windows.Window(xoff, yoff, width, height)


def intersect_bounds(b1, b2, transform):
    # Based on gdal_merge.py
    int_w = max(b1[0], b2[0])
    int_e = min(b1[2], b2[2])
    if int_w >= int_e:
        raise ValueError

    if transform.e < 0:
        # north up
        int_s = max(b1[1], b2[1])
        int_n = min(b1[3], b2[3])
        if int_s >= int_n:
            raise ValueError
    else:
        int_s = min(b1[1], b2[1])
        int_n = max(b1[3], b2[3])
        if int_n >= int_s:
            raise ValueError

    return int_w, int_s, int_e, int_n
