"""File translation command"""

import logging
import warnings

import click
from cligj import files_inout_arg, format_opt

from .helpers import resolve_inout
from . import options
import rasterio


warnings.simplefilter('default')


@click.command(short_help="Copy a raster dataset with translations.")
@click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=True),
    required=True,
    metavar="INPUT OUTPUT")
@options.output_opt
@format_opt
@options.dtype_opt
@click.option('--scale-linear', 'scaling', flag_value='linear',
              help="Scale intensity of raster values.", show_default=True)
@click.option(
    '--src-scale-points', 'src_points', nargs=2, type=float, default=None,
    help="Source points for intensity scaling [default: full range].")
@click.option(
    '--dst-scale-points', 'dst_points', nargs=2, type=float, default=None,
    help="Destination points for intensity scaling [default: full range].")
@options.creation_options
@click.pass_context
def convert(
        ctx, files, output, driver, dtype, scaling, src_points, dst_points,
        creation_options):
    """Copy and convert raster datasets to other data types and formats.

    Data values may be linearly scaled when copying by using the
    --scale-linear option. The default is to scale the full input range
    to the full output range, eg, uint16's 0-65,535 to uint8's 0-255.
    A different scaling can be performed by using the --src-scale-points
    and --dst-scale-points options. For example, to scale uint16 data with
    an actual range of 0-10,000 to 0-100 as uint8:

      --scale-linear --src-scale-points 0 10000 --dst-scale-points 0 100

    Format specific creation options may also be passed using --co. To tile
    a new GeoTIFF output file, do the following.

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

                data = data.astype(dst_dtype, copy=False)

                if scaling == 'linear':
                    # Determine our rescaling ranges. As the data types
                    # must be known, this is less difficult to do here
                    # than in an option validating callback.
                    import numpy as np
                    infos = {'c': np.finfo, 'f': np.finfo, 'i': np.iinfo,
                             'u': np.iinfo}

                    if not src_points:
                        rng = infos[np.dtype(src.meta['dtype']).kind](
                            src.meta['dtype'])
                        src_points = rng.min, rng.max

                    if not dst_points:
                        rng = infos[np.dtype(dst_dtype).kind](dst_dtype)
                        dst_points = rng.min, rng.max

                    scale_slope = ((dst_points[1] - dst_points[0]) /
                                   (src_points[1] - src_points[0]))
                    scale_intercept = (
                        dst_points[0] - scale_slope * src_points[0])

                    np.multiply(data, scale_slope, out=data, casting='unsafe')
                    np.add(data, scale_intercept, out=data, casting='unsafe')

                dst.write(data)
