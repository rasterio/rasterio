# Merge command.

import logging
import math
import os.path
import sys

import click
from cligj import files_inout_arg, format_opt

import rasterio
from rasterio.rio.cli import cli
from rasterio.transform import Affine


@cli.command(short_help="Merge a stack of raster datasets.")
@files_inout_arg
@format_opt
@click.option('--bounds', nargs=4, type=float, default=None,
              help="Output bounds: left, bottom, right, top.")
@click.option('--res', nargs=2, type=float, default=None,
              help="Output dataset resolution: pixel width, pixel height")
@click.pass_context
def merge(ctx, files, driver, bounds, res):
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

            if os.path.exists(output):
                # TODO: prompt user to update existing file (-i option) like:
                # overwrite b.tif? (y/n [n]) n
                # not overwritten
                dst = rasterio.open(output, 'r+')
                nodataval = dst.nodatavals[0]
                dest = np.zeros((dst.count,) + dst.shape,
                        dtype=dst.dtypes[0])
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

                dst = rasterio.open(output, 'w', **kwargs)
                dest = np.zeros((first.count, output_height, output_width),
                        dtype=first.dtypes[0])
                nodataval = first.nodatavals[0]

            if nodataval is not None:
                dest.fill(nodataval)
            else:
                notdataval = 0

            for fname in reversed(files):
                with rasterio.open(fname) as src:
                    # Real World (tm) use of boundless reads.
                    # This approach uses the maximum amount of memory to solve
                    # the problem. Making it more efficient is a TODO.
                    window = src.window(*dst.bounds)
                    data = np.zeros_like(dest)
                    data = src.read(
                            out=data,
                            window=window,
                            boundless=True,
                            masked=True)
                    np.copyto(dest, data,
                        where=np.logical_and(
                        dest==nodataval, data.mask==False))

            if dst.mode == 'r+':
                data = dst.read(masked=True)
                np.copyto(dest, data,
                    where=np.logical_and(
                    dest==nodataval, data.mask==False))

            dst.write(dest)
            dst.close()

        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
