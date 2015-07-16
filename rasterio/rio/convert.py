"""File translation command"""

import logging
import warnings

import click
from cligj import files_inout_arg, format_opt
import numpy as np

from .helpers import resolve_inout
from . import options
import rasterio


warnings.simplefilter('default')


@click.command(short_help="Copy and convert raster dataset.")
@click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=True),
    required=True,
    metavar="INPUT OUTPUT")
@options.output_opt
@format_opt
@options.dtype_opt
@click.option('--scale-ratio', type=float, default=None,
              help="Source to destination scaling ratio.")
@click.option('--scale-offset', type=float, default=None,
              help="Source to destination scaling offset.")
@options.creation_options
@click.pass_context
def convert(
        ctx, files, output, driver, dtype, scale_ratio, scale_offset,
        creation_options):
    """Copy and convert raster datasets to other data types and formats.

    Data values may be linearly scaled when copying by using the
    --scale-ratio and --scale-offset options. Destination raster values
    are calculated as

      dst = scale_ratio * src + scale_offset

    For example, to scale uint16 data with an actual range of 0-4095 to
    0-255 as uint8:

      $ rio convert in16.tif out8.tif --dtype uint8 --scale-ratio 0.0625

    Format specific creation options may also be passed using --co. To
    tile a new GeoTIFF output file, do the following.

      --co tiled=true --co blockxsize=256 --co blockysize=256

    To compress it using the LZW method, add

      --co compress=LZW

    """
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    with rasterio.drivers(CPL_DEBUG=verbosity > 2):
        outputfile, files = resolve_inout(files=files, output=output)
        inputfile = files[0]

        with rasterio.open(inputfile) as src:
            profile = src.meta

            if 'affine' in profile:
                profile['transform'] = profile.pop('affine')

            if driver:
                profile['driver'] = driver

            if dtype:
                profile['dtype'] = dtype
            dst_dtype = profile['dtype']

            # Update profile with command line creation options.
            profile.update(**creation_options)

            with rasterio.open(outputfile, 'w', **profile) as dst:

                data = src.read()

                if scale_ratio:
                    # Add a very small epsilon to 
                    data = data.astype('float64', casting='unsafe')
                    np.multiply(
                        data, scale_ratio, out=data, casting='unsafe')

                if scale_offset:
                    np.add(
                        data, scale_offset, out=data, casting='unsafe')

                result = data.astype(dst_dtype, casting='unsafe', copy=False)

                dst.write(result)
