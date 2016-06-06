"""Merge command."""

import logging

import click
from cligj import files_inout_arg, format_opt

import rasterio

from . import options
from .helpers import resolve_inout


@click.command(short_help="Merge a stack of raster datasets.")
@files_inout_arg
@options.output_opt
@format_opt
@options.bounds_opt
@options.resolution_opt
@options.nodata_opt
@options.force_overwrite_opt
@click.option('--precision', type=int, default=7,
              help="Number of decimal places of precision in alignment of "
                   "pixels")
@options.creation_options
@click.pass_context
def merge(ctx, files, output, driver, bounds, res, nodata, force_overwrite,
          precision, creation_options):
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

    \b
      --res 0.1 0.1  => --res 0.1 (square)
      --res 0.1 0.2  => --res 0.1 --res 0.2  (rectangular)
    """
    from rasterio.merge import merge as merge_tool

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1

    output, files = resolve_inout(
        files=files, output=output, force_overwrite=force_overwrite)

    with rasterio.Env(CPL_DEBUG=verbosity > 2):
        sources = [rasterio.open(f) for f in files]
        dest, output_transform = merge_tool(sources, bounds=bounds, res=res,
                                            nodata=nodata, precision=precision)

        profile = sources[0].profile
        profile.pop('affine')
        profile['transform'] = output_transform
        profile['height'] = dest.shape[1]
        profile['width'] = dest.shape[2]
        profile['driver'] = driver

        profile.update(**creation_options)

        with rasterio.open(output, 'w', **profile) as dst:
            dst.write(dest)
