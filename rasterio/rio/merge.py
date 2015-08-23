# Merge command.

import logging
import math
import os.path
import warnings

import click
from cligj import files_inout_arg, format_opt

from .helpers import resolve_inout
from . import options
import rasterio
from rasterio.transform import Affine
from rasterio.merge import merge as merge_tool


@click.command(short_help="Merge a stack of raster datasets.")
@files_inout_arg
@options.output_opt
@format_opt
@options.bounds_opt
@options.resolution_opt
@click.option('--nodata', type=float, default=None,
              help="Override nodata values defined in input datasets")
@options.creation_options
@click.pass_context
def merge(ctx, files, output, driver, bounds, res, nodata, creation_options):
    """Copy valid pixels from input files to an output file.

    All files must have the same number of bands, data type, and
    coordinate reference system.

    Input files are merged in their listed order using the reverse
    painter's algorithm. If the output file exists, its values will be
    overwritten by input values.

    Geospatial bounds and resolution of a new output file in the
    units of the input file coordinate reference system may be provided
    and are otherwise taken from the first input file.

    Note: --res changed from 2 parameters in 0.25.
      --res 0.1 0.1  => --res 0.1 (square)
      --res 0.1 0.2  => --res 0.1 --res 0.2  (rectangular)
    """

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    output, files = resolve_inout(files=files, output=output)

    try:
        sources = [rasterio.open(f) for f in files]
        dest, output_transform = merge_tool(sources, bounds=bounds, res=res,
                                            nodata=nodata)
        kwargs = sources[0].meta
        kwargs.update(**creation_options)
        kwargs.pop('affine')
        kwargs['transform'] = output_transform
        kwargs['height'] = dest.shape[1]
        kwargs['width'] = dest.shape[2]
        kwargs['driver'] = driver

        dst = rasterio.open(output, 'w', **kwargs)
        dst.write(dest)
        dst.close()
    except:
        logger.exception("Exception caught during processing")
        raise click.Abort()
