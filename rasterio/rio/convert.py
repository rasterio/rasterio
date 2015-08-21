"""File translation command"""

import logging
import warnings

import click
from cligj import format_opt
import numpy as np

from .helpers import resolve_inout
from . import options
import rasterio
from rasterio.coords import disjoint_bounds


warnings.simplefilter('default')


# Clip command
@click.command(short_help='Clip a raster to given bounds.')
@click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=True),
    required=True,
    metavar="INPUT OUTPUT")
@options.output_opt
@options.bounds_opt
@click.option(
    '--like',
    type=click.Path(exists=True),
    help='Raster dataset to use as a template for bounds')
@format_opt
@options.creation_options
@click.pass_context
def clip(
        ctx,
        files,
        output,
        bounds,
        like,
        driver,
        creation_options):
    """Clips a raster using bounds input directly or from a template raster.

    \b
      $ rio clip input.tif output.tif --bounds xmin ymin xmax ymax
      $ rio clip input.tif output.tif --like template.tif

    If using --bounds, values must be in coordinate reference system of input.
    If using --like, bounds will automatically be transformed to match the
    coordinate reference system of the input.

    It can also be combined to read bounds of a feature dataset using Fiona:

    \b
      $ rio clip input.tif output.tif --bounds $(fio info features.shp --bounds)

    """

    from rasterio.warp import transform_bounds

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1

    with rasterio.drivers(CPL_DEBUG=verbosity > 2):

        output, files = resolve_inout(files=files, output=output)
        input = files[0]

        with rasterio.open(input) as src:
            if bounds:
                if disjoint_bounds(bounds, src.bounds):
                    raise click.BadParameter('must overlap the extent of '
                                             'the input raster',
                                             param='--bounds',
                                             param_hint='--bounds')
            elif like:
                with rasterio.open(like) as template_ds:
                    bounds = template_ds.bounds
                    if template_ds.crs != src.crs:
                        bounds = transform_bounds(template_ds.crs, src.crs,
                                                  *bounds)

                    if disjoint_bounds(bounds, src.bounds):
                        raise click.BadParameter('must overlap the extent of '
                                                 'the input raster',
                                                 param='--like',
                                                 param_hint='--like')

            else:
                raise click.UsageError('--bounds or --like required')

            window = src.window(*bounds)

            out_kwargs = src.meta.copy()
            out_kwargs.update({
                'driver': driver,
                'height': window[0][1] - window[0][0],
                'width': window[1][1] - window[1][0],
                'transform': src.window_transform(window)
            })
            out_kwargs.update(**creation_options)

            with rasterio.open(output, 'w', **out_kwargs) as out:
                out.write(src.read(window=window))


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
@options.rgb_opt
@options.creation_options
@click.pass_context
def convert(
        ctx, files, output, driver, dtype, scale_ratio, scale_offset,
        photometric, creation_options):
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

            # Use the input file's profile, updated by CLI
            # options, as the profile for the output file.
            profile = src.profile

            if 'affine' in profile:
                profile['transform'] = profile.pop('affine')

            if driver:
                profile['driver'] = driver

            if dtype:
                profile['dtype'] = dtype
            dst_dtype = profile['dtype']

            if photometric:
                creation_options['photometric'] = photometric

            profile.update(**creation_options)

            with rasterio.open(outputfile, 'w', **profile) as dst:

                data = src.read()

                if scale_ratio:
                    # Cast to float64 before multiplying.
                    data = data.astype('float64', casting='unsafe', copy=False)
                    np.multiply(
                        data, scale_ratio, out=data, casting='unsafe')

                if scale_offset:
                    # My understanding of copy=False is that this is a
                    # no-op if the array was cast for multiplication.
                    data = data.astype('float64', casting='unsafe', copy=False)
                    np.add(
                        data, scale_offset, out=data, casting='unsafe')

                # Cast to the output dtype and write.
                result = data.astype(dst_dtype, casting='unsafe', copy=False)
                dst.write(result)
