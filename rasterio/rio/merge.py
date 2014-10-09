# Merge command.

import logging
import os.path
import sys

import click

import rasterio

from rasterio.rio.cli import cli


@cli.command(short_help="Merge a stack of raster datasets.")
@click.argument('input', nargs=-1,
    type=click.Path(exists=True, resolve_path=True), required=True)
@click.option('-o','--output',
    type=click.Path(exists=False, resolve_path=True), required=True,
    help="Path to output file.")
@click.option('--driver', default='GTiff', help="Output format driver")
@click.pass_context
def merge(ctx, input, output, driver):
    """Copy valid pixels from input files to the output file.

    All files must have the same shape, number of bands, and data type.

    Input files are merged in their listed order using a reverse
    painter's algorithm.
    """
    import numpy as np

    verbosity = ctx.obj['verbosity']
    logger = logging.getLogger('rio')
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):

            with rasterio.open(input[0]) as first:
                kwargs = first.meta
                kwargs['transform'] = kwargs.pop('affine')
                dest = np.empty((3,) + first.shape, dtype=first.dtypes[0])

            if os.path.exists(output):
                dst = rasterio.open(output, 'r+')
                nodataval = dst.nodatavals[0]
            else:
                kwargs['driver'] == driver
                dst = rasterio.open(output, 'w', **kwargs)
                nodataval = first.nodatavals[0]

            dest.fill(nodataval)

            for fname in reversed(input):
                with rasterio.open(fname) as src:
                    data = src.read()
                    np.copyto(dest, data,
                        where=np.logical_and(
                        dest==nodataval, data.mask==False))

            if dst.mode == 'r+':
                data = dst.read()
                np.copyto(dest, data,
                    where=np.logical_and(
                    dest==nodataval, data.mask==False))

            dst.write(dest)
            dst.close()

        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)

