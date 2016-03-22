import logging
from math import ceil
import warnings

import click
from cligj import files_inout_arg, format_opt

from .helpers import resolve_inout
from . import options
import rasterio
from rasterio import crs
from rasterio.transform import Affine
from rasterio.warp import (reproject, Resampling, calculate_default_transform,
   transform_bounds)


# Improper usage of rio-warp can lead to accidental creation of
# extremely large datasets. We'll put a hard limit on the size of
# datasets and raise a usage error if the limits are exceeded.
MAX_OUTPUT_WIDTH = 100000
MAX_OUTPUT_HEIGHT = 100000


def bounds_handler(ctx, param, value):
    """Warn about future usage changes."""
    if value:
        click.echo("Future Warning: "
            "the semantics of the `--bounds` option will change in Rasterio "
            "version 1.0 from bounds of the source dataset to bounds of the "
            "destination dataset.", err=True)
    return value


def x_dst_bounds_handler(ctx, param, value):
    """Warn about future usage changes."""
    if value:
        click.echo("Future Warning: "
            "the `--x-dst-bounds` option will be removed in Rasterio version "
            "1.0 in favor of `--bounds`.", err=True)
    return value


@click.command(short_help='Warp a raster dataset.')
@files_inout_arg
@options.output_opt
@format_opt
@options.like_file_opt
@click.option('--dst-crs', default=None,
              help='Target coordinate reference system.')
@options.dimensions_opt
@click.option(
    '--src-bounds',
    nargs=4, type=float, default=None,
    help="Determine output extent from source bounds: left bottom right top "
         "(note: for future backwards compatibility in 1.0).")
@click.option(
    '--x-dst-bounds',
    nargs=4, type=float, default=None, callback=x_dst_bounds_handler,
    help="Set output extent from bounding values: left bottom right top "
         "(note: this option will be removed in 1.0).")
@click.option(
    '--bounds',
    nargs=4, type=float, default=None, callback=bounds_handler,
    help="Determine output extent from source bounds: left bottom right top "
         "(note: the semantics of this option will change to those of "
         "`--x-dst-bounds` in version 1.0).")
@options.resolution_opt
@click.option('--resampling', type=click.Choice([r.name for r in Resampling]),
              default='nearest', help="Resampling method.",
              show_default=True)
@click.option('--threads', type=int, default=1,
              help='Number of processing threads.')
@click.option('--check-invert-proj', type=bool, default=True,
              help='Constrain output to valid coordinate region in dst-crs')
@options.force_overwrite_opt
@options.creation_options
@click.pass_context
def warp(ctx, files, output, driver, like, dst_crs, dimensions, src_bounds,
         x_dst_bounds, bounds, res, resampling, threads, check_invert_proj,
         force_overwrite, creation_options):
    """
    Warp a raster dataset.

    If a template raster is provided using the --like option, the
    coordinate reference system, affine transform, and dimensions of
    that raster will be used for the output.  In this case --dst-crs,
    --bounds, --res, and --dimensions options are ignored.

    \b
        $ rio warp input.tif output.tif --like template.tif

    The output coordinate reference system may be either a PROJ.4 or
    EPSG:nnnn string,

    \b
        --dst-crs EPSG:4326
        --dst-crs '+proj=longlat +ellps=WGS84 +datum=WGS84'

    or a JSON text-encoded PROJ.4 object.

    \b
        --dst-crs '{"proj": "utm", "zone": 18, ...}'

    If --dimensions are provided, --res and --bounds are ignored.
    Resolution is calculated based on the relationship between the
    raster bounds in the target coordinate system and the dimensions,
    and may produce rectangular rather than square pixels.

    \b
        $ rio warp input.tif output.tif --dimensions 100 200 \\
        > --dst-crs EPSG:4326

    If --bounds are provided, --res is required if --dst-crs is provided
    (defaults to source raster resolution otherwise).

    \b
        $ rio warp input.tif output.tif \\
        > --bounds -78 22 -76 24 --res 0.1 --dst-crs EPSG:4326

    """

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    output, files = resolve_inout(
        files=files, output=output, force_overwrite=force_overwrite)

    resampling = Resampling[resampling]  # get integer code for method

    if not len(res):
        # Click sets this as an empty tuple if not provided
        res = None
    else:
        # Expand one value to two if needed
        res = (res[0], res[0]) if len(res) == 1 else res

    with rasterio.drivers(CPL_DEBUG=verbosity > 2,
                          CHECK_WITH_INVERT_PROJ=check_invert_proj):
        with rasterio.open(files[0]) as src:
            l, b, r, t = src.bounds
            out_kwargs = src.meta.copy()
            out_kwargs['driver'] = driver

            # Sort out the bounds options.
            src_bounds = bounds or src_bounds
            dst_bounds = x_dst_bounds
            if src_bounds and dst_bounds:
                raise click.BadParameter(
                    "Source and destination bounds may not be specified "
                    "simultaneously.")

            if like:
                with rasterio.open(like) as template_ds:
                    dst_crs = template_ds.crs
                    dst_transform = template_ds.affine
                    dst_height = template_ds.height
                    dst_width = template_ds.width

            elif dst_crs:
                try:
                    dst_crs = crs.from_string(dst_crs)
                except ValueError:
                    raise click.BadParameter("invalid crs format.",
                                             param=dst_crs, param_hint=dst_crs)

                if dimensions:
                    # Calculate resolution appropriate for dimensions
                    # in target.
                    dst_width, dst_height = dimensions
                    xmin, ymin, xmax, ymax = transform_bounds(src.crs, dst_crs,
                                                              *src.bounds)
                    dst_transform = Affine(
                        (xmax - xmin) / float(dst_width),
                        0, xmin, 0,
                        (ymin - ymax) / float(dst_height),
                        ymax
                    )

                elif src_bounds or dst_bounds:
                    if not res:
                        raise click.BadParameter(
                            "Required when using --bounds.",
                            param='res', param_hint='res')

                    if src_bounds:
                        xmin, ymin, xmax, ymax = transform_bounds(
                            src.crs, dst_crs, *src_bounds)
                    else:
                        xmin, ymin, xmax, ymax = dst_bounds

                    dst_transform = Affine(res[0], 0, xmin, 0, -res[1], ymax)
                    dst_width = max(int(ceil((xmax - xmin) / res[0])), 1)
                    dst_height = max(int(ceil((ymax - ymin) / res[1])), 1)

                else:
                    dst_transform, dst_width, dst_height = calculate_default_transform(
                        src.crs, dst_crs, src.width, src.height, *src.bounds,
                        resolution=res)

            elif dimensions:
                # Same projection, different dimensions, calculate resolution.
                dst_crs = src.crs
                dst_width, dst_height = dimensions
                dst_transform = Affine(
                    (r - l) / float(dst_width),
                    0, l, 0,
                    (b - t) / float(dst_height),
                    t
                )

            elif src_bounds or dst_bounds:
                # Same projection, different dimensions and possibly
                # different resolution.
                if not res:
                    res = (src.affine.a, -src.affine.e)

                dst_crs = src.crs
                xmin, ymin, xmax, ymax = (src_bounds or dst_bounds)
                dst_transform = Affine(res[0], 0, xmin, 0, -res[1], ymax)
                dst_width = max(int(ceil((xmax - xmin) / res[0])), 1)
                dst_height = max(int(ceil((ymax - ymin) / res[1])), 1)

            elif res:
                # Same projection, different resolution.
                dst_crs = src.crs
                dst_transform = Affine(res[0], 0, l, 0, -res[1], t)
                dst_width = max(int(ceil((r - l) / res[0])), 1)
                dst_height = max(int(ceil((t - b) / res[1])), 1)

            else:
                dst_crs = src.crs
                dst_transform = src.affine
                dst_width = src.width
                dst_height = src.height

            # When the bounds option is misused, extreme values of
            # destination width and height may result.
            if (dst_width < 0 or dst_height < 0 or
                    dst_width > MAX_OUTPUT_WIDTH or
                    dst_height > MAX_OUTPUT_HEIGHT):
                raise click.BadParameter(
                    "Invalid output dimensions: {0}.".format(
                        (dst_width, dst_height)))

            out_kwargs.update({
                'crs': dst_crs,
                'transform': dst_transform,
                'affine': dst_transform,
                'width': dst_width,
                'height': dst_height
            })

            out_kwargs.update(**creation_options)

            with rasterio.open(output, 'w', **out_kwargs) as dst:
                for i in range(1, src.count + 1):

                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.affine,
                        src_crs=src.crs,
                        # src_nodata=#TODO
                        dst_transform=out_kwargs['transform'],
                        dst_crs=out_kwargs['crs'],
                        # dst_nodata=#TODO
                        resampling=resampling,
                        num_threads=threads)
