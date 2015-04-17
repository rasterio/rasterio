# Merge command.

import logging
import math
import os.path
import sys
import warnings

import click
from cligj import files_inout_arg, format_opt

import rasterio
from rasterio.rio.cli import cli
from rasterio.transform import Affine


@cli.command(short_help="Merge a stack of raster datasets.")
@files_inout_arg
@format_opt
@click.option('-bd', '--bounds', nargs=4, type=float, default=None,
              help="Output bounds: left, bottom, right, top.")
@click.option('-r', '--res', nargs=2, type=float, default=None,
              help="Output dataset resolution: pixel width, pixel height")
@click.option('-nd', '--nodata', type=float, default=None,
              help="Override nodata values defined in input datasets")
@click.pass_context
def merge(ctx, files, driver, bounds, res, nodata):
    """Copy valid pixels from input files to an output file.

    All files must have the same number of bands, data type, and
    coordinate reference system.

    Input files are merged in their listed order using the reverse
    painter's algorithm. If the output file exists, its values will be
    overwritten by input values.

    Geospatial bounds and resolution of a new output file in the
    units of the input file coordinate reference system may be provided
    and are otherwise taken from the first input file.
    """
    import numpy as np

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            output = files[-1]
            files = files[:-1]

            with rasterio.open(files[0]) as first:
                first_res = first.res
                kwargs = first.meta
                kwargs.pop('affine')
                nodataval = first.nodatavals[0]
                dtype = first.dtypes[0]

            if os.path.exists(output):
                # TODO: prompt user to update existing file (-i option) like:
                # overwrite b.tif? (y/n [n]) n
                # not overwritten
                dst = rasterio.open(output, 'r+')
                nodataval = dst.nodatavals[0]
                dtype = dst.dtypes[0]
                dest = np.zeros((dst.count,) + dst.shape, dtype=dtype)
            else:
                # Create new output file.
                # Extent from option or extent of all inputs.
                if not bounds:
                    # scan input files.
                    xs = []
                    ys = []
                    for f in files:
                        with rasterio.open(f) as src:
                            left, bottom, right, top = src.bounds
                            xs.extend([left, right])
                            ys.extend([bottom, top])
                    bounds = min(xs), min(ys), max(xs), max(ys)
                output_transform = Affine.translation(bounds[0], bounds[3])

                # Resolution/pixel size.
                if not res:
                    res = first_res
                output_transform *= Affine.scale(res[0], -res[1])

                # Dataset shape.
                output_width = int(math.ceil((bounds[2]-bounds[0])/res[0]))
                output_height = int(math.ceil((bounds[3]-bounds[1])/res[1]))

                kwargs['driver'] == driver
                kwargs['transform'] = output_transform
                kwargs['width'] = output_width
                kwargs['height'] = output_height

                logger.debug("Kwargs: %r", kwargs)
                logger.debug("bounds: %r", bounds)
                logger.debug("Res: %r", res)

                dst = rasterio.open(output, 'w', **kwargs)
                dest = np.zeros((first.count, output_height, output_width),
                        dtype=dtype)

                logger.debug("In merge, dest shape: %r", dest.shape)

            if nodata is not None:
                nodataval = nodata

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

            dst_w, dst_s, dst_e, dst_n = dst.bounds

            for fname in reversed(files):
                with rasterio.open(fname) as src:
                    # Real World (tm) use of boundless reads.
                    # This approach uses the maximum amount of memory to solve
                    # the problem. Making it more efficient is a TODO.

                    # 1. Compute spatial intersection of destination
                    #    and source.
                    src_w, src_s, src_e, src_n = src.bounds

                    int_w = src_w if src_w > dst_w else dst_w
                    int_s = src_s if src_s > dst_s else dst_s
                    int_e = src_e if src_e < dst_e else dst_e
                    int_n = src_n if src_n < dst_n else dst_n

                    # 2. Compute the source window.
                    src_window = src.window(int_w, int_s, int_e, int_n)

                    # 3. Compute the destination window.
                    dst_window = dst.window(int_w, int_s, int_e, int_n)

                    # 4. Initialize temp array.
                    temp = np.zeros(
                            (first.count,) + tuple(b - a for a, b in dst_window),
                            dtype=dtype)

                    temp = src.read(
                            out=temp,
                            window=src_window,
                            boundless=False,
                            masked=True)

                    # 5. Copy elements of temp into dest.
                    roff, coff = dst.index(int_w, int_n)
                    h, w = temp.shape[-2:]

                    region = dest[:,roff:roff+h,coff:coff+w]
                    np.copyto(region, temp,
                        where=np.logical_and(
                        region==nodataval, temp.mask==False))

            if dst.mode == 'r+':
                temp = dst.read(masked=True)
                np.copyto(dest, temp,
                    where=np.logical_and(
                    dest==nodataval, temp.mask==False))

            dst.write(dest)
            dst.close()

        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
