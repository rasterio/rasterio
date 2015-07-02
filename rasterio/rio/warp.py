import logging
from math import ceil
import click
from cligj import format_opt

from . import options
import rasterio
from rasterio import crs
from rasterio.transform import Affine
from rasterio.warp import (reproject, RESAMPLING, calculate_default_transform,
   transform_bounds)


logger = logging.getLogger('rio')


@click.command(short_help='Warp a raster dataset.')
@options.file_in_arg
@options.file_out_arg
@format_opt
@options.like_file_opt
@click.option('--dst-crs', default=None,
              help='Target coordinate reference system.  Default: EPSG:4326')
@options.dimensions_opt
@options.bounds_opt
#TODO: flag for bounds in target
@options.resolution_opt
@click.option('--resampling', type=click.Choice(['nearest', 'bilinear', 'cubic',
                'cubic_spline','lanczos', 'average', 'mode']),
              default='nearest', help='Resampling method')
@click.option('--threads', type=int, default=1,
              help='Number of processing threads.')
@click.pass_context
def warp(
        ctx,
        input,
        output,
        driver,
        like,
        dst_crs,
        dimensions,
        bounds,
        res,
        resampling,
        threads):
    """
    Warp a raster dataset.

    The output is always overwritten.

    If a template raster is provided using the --like option, the coordinate
    reference system, affine transform, and dimensions of that raster will
    be used for the output.  In this case --dst-crs, --bounds, --res, and
    --dimensions options are ignored.

    If --dimensions are provided, --res and --bounds are ignored.  Resolution
    is calculated based on the relationship between the source raster bounds
    and dimensions, and may produce rectangular rather than square pixels.

    If --bounds are provided, --res is required if --dst-crs is provided
    (defaults to source raster resolution otherwise).  Bounds are in the source
    coordinate reference system.
    """

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    resampling = getattr(RESAMPLING, resampling)  # get integer code for method

    if not len(res):
        # Click sets this as an empty tuple if not provided
        res = None
    else:
        # Expand one value to two if needed
        res = (res[0], res[0]) if len(res) == 1 else res

    with rasterio.drivers(CPL_DEBUG=verbosity > 2):
        with rasterio.open(input) as src:
            l, b, r, t = src.bounds
            out_kwargs = src.meta.copy()
            out_kwargs['driver'] = driver

            if like:
                with rasterio.open(like) as template_ds:
                    dst_crs = template_ds.crs
                    dst_transform = template_ds.affine
                    dst_height = template_ds.height
                    dst_width = template_ds.width

            elif dst_crs:
                if dimensions:
                    # Calculate resolution appropriate for dimensions in target
                    dst_width, dst_height = dimensions
                    xmin, ymin, xmax, ymax = transform_bounds(src.crs, dst_crs,
                                                              *src.bounds)
                    dst_transform = Affine(
                        (xmax - xmin) / float(dst_width),
                        0, xmin, 0,
                        (ymin - ymax) / float(dst_height),
                        ymax
                    )

                elif bounds:
                    if not res:
                        raise click.BadParameter('Required when using --bounds',
                            param='res', param_hint='res')

                    xmin, ymin, xmax, ymax = transform_bounds(src.crs, dst_crs,
                                                              *bounds)
                    dst_transform = Affine(res[0], 0, xmin, 0, -res[1], ymax)
                    dst_width = max(int(ceil((xmax - xmin) / res[0])), 1)
                    dst_height = max(int(ceil((ymax - ymin) / res[1])), 1)

                else:
                    dst_crs = crs.from_string(dst_crs)
                    dst_transform, dst_width, dst_height = calculate_default_transform(
                        src.crs, dst_crs, src.width, src.height, *src.bounds,
                        resolution=res)

            elif dimensions:
                # Same projection, different dimensions, calculate resolution
                dst_crs = src.crs
                dst_width, dst_height = dimensions
                dst_transform = Affine(
                    (r - l) / float(dst_width),
                    0, l, 0,
                    (b - t) / float(dst_height),
                    t
                )

            elif bounds:
                # Same projection, different dimensions and possibly different
                # resolution
                if not res:
                    res = (src.affine.a, -src.affine.e)

                dst_crs = src.crs
                xmin, ymin, xmax, ymax = bounds
                dst_transform = Affine(res[0], 0, xmin, 0, -res[1], ymax)
                dst_width = max(int(ceil((xmax - xmin) / res[0])), 1)
                dst_height = max(int(ceil((ymax - ymin) / res[1])), 1)

            elif res:
                # Same projection, different resolution
                dst_crs = src.crs
                dst_transform = Affine(res[0], 0, l, 0, -res[1], t)
                dst_width = max(int(ceil((r - l) / res[0])), 1)
                dst_height = max(int(ceil((t - b) / res[1])), 1)

            else:
                dst_crs = src.crs
                dst_transform = src.affine
                dst_width = src.width
                dst_height = src.height

            out_kwargs.update({
                'crs': dst_crs,
                'transform': dst_transform,
                'affine': dst_transform,
                'width': dst_width,
                'height': dst_height
            })

            with rasterio.open(output, 'w', **out_kwargs) as dst:
                for i in range(1, src.count + 1):
                    click.echo('Warping band {0}...'.format(i))

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