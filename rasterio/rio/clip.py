"""File translation command"""

import click
from cligj import format_opt

from .helpers import resolve_inout
from . import options
import rasterio
from rasterio.coords import disjoint_bounds


# Clip command
@click.command(short_help='Clip a raster to given bounds.')
@click.argument(
    'files',
    nargs=-1,
    type=click.Path(),
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
    aws_session = (ctx.obj and ctx.obj.get('aws_session'))

    with rasterio.drivers(CPL_DEBUG=verbosity > 2), aws_session:

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
