import json
import logging
from math import ceil
import os

import click
import cligj

from .helpers import resolve_inout
from . import options
import rasterio
from rasterio.transform import Affine
from rasterio.coords import disjoint_bounds


logger = logging.getLogger('rio')


# Common options used below

# Unlike the version in cligj, this one doesn't require values.
files_inout_arg = click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=True),
    metavar="INPUTS... OUTPUT")


@click.command(short_help='Rasterize features.')
@files_inout_arg
@options.output_opt
@cligj.format_opt
@options.like_file_opt
@options.bounds_opt
@options.dimensions_opt
@options.resolution_opt
@click.option('--src-crs', '--src_crs', 'src_crs', default=None,
              help='Source coordinate reference system.  Limited to EPSG '
              'codes for now.  Used as output coordinate system if output '
              'does not exist or --like option is not used. '
              'Default: EPSG:4326')
@options.all_touched_opt
@click.option('--default-value', '--default_value', 'default_value',
              type=float, default=1, help='Default value for rasterized pixels')
@click.option('--fill', type=float, default=0,
              help='Fill value for all pixels not overlapping features.  Will '
              'be evaluated as NoData pixels for output.  Default: 0')
@click.option('--property', 'prop', type=str, default=None, help='Property in '
              'GeoJSON features to use for rasterized values.  Any features '
              'that lack this property will be given --default_value instead.')
@options.force_overwrite_opt
@options.creation_options
@click.pass_context
def rasterize(
        ctx,
        files,
        output,
        driver,
        like,
        bounds,
        dimensions,
        res,
        src_crs,
        all_touched,
        default_value,
        fill,
        prop,
        force_overwrite,
        creation_options):
    """Rasterize GeoJSON into a new or existing raster.

    If the output raster exists, rio-rasterize will rasterize feature values
    into all bands of that raster.  The GeoJSON is assumed to be in the same
    coordinate reference system as the output unless --src-crs is provided.

    --default_value or property values when using --property must be using a
    data type valid for the data type of that raster.


    If a template raster is provided using the --like option, the affine
    transform and data type from that raster will be used to create the output.
    Only a single band will be output.

    The GeoJSON is assumed to be in the same coordinate reference system unless
    --src-crs is provided.

    --default_value or property values when using --property must be using a
    data type valid for the data type of that raster.

    --driver, --bounds, --dimensions, and --res are ignored when output exists
    or --like raster is provided


    If the output does not exist and --like raster is not provided, the input
    GeoJSON will be used to determine the bounds of the output unless
    provided using --bounds.

    --dimensions or --res are required in this case.

    If --res is provided, the bottom and right coordinates of bounds are
    ignored.


    Note:
    The GeoJSON is not projected to match the coordinate reference system
    of the output or --like rasters at this time.  This functionality may be
    added in the future.
    """
    from rasterio._base import is_geographic_crs, is_same_crs
    from rasterio.features import rasterize
    from rasterio.features import bounds as calculate_bounds

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1

    output, files = resolve_inout(
        files=files, output=output, force_overwrite=force_overwrite)

    has_src_crs = src_crs is not None
    src_crs = src_crs or 'EPSG:4326'

    # If values are actually meant to be integers, we need to cast them
    # as such or rasterize creates floating point outputs
    if default_value == int(default_value):
        default_value = int(default_value)
    if fill == int(fill):
        fill = int(fill)

    with rasterio.Env(CPL_DEBUG=verbosity > 2):

        def feature_value(feature):
            if prop and 'properties' in feature:
                return feature['properties'].get(prop, default_value)
            return default_value

        with click.open_file(files.pop(0) if files else '-') as gj_f:
            geojson = json.loads(gj_f.read())
        if 'features' in geojson:
            geometries = []
            for f in geojson['features']:
                geometries.append((f['geometry'], feature_value(f)))
        elif 'geometry' in geojson:
            geometries = ((geojson['geometry'], feature_value(geojson)), )
        else:
            raise click.BadParameter('Invalid GeoJSON', param=input,
                                     param_hint='input')

        geojson_bounds = geojson.get('bbox', calculate_bounds(geojson))

        if os.path.exists(output):
            with rasterio.open(output, 'r+') as out:
                if has_src_crs and not is_same_crs(src_crs, out.crs):
                    raise click.BadParameter('GeoJSON does not match crs of '
                                             'existing output raster',
                                             param='input', param_hint='input')

                if disjoint_bounds(geojson_bounds, out.bounds):
                    click.echo("GeoJSON outside bounds of existing output "
                               "raster. Are they in different coordinate "
                               "reference systems?",
                               err=True)

                meta = out.meta.copy()

                result = rasterize(
                    geometries,
                    out_shape=(meta['height'], meta['width']),
                    transform=meta.get('affine', meta['transform']),
                    all_touched=all_touched,
                    dtype=meta.get('dtype', None),
                    default_value=default_value,
                    fill=fill)

                for bidx in range(1, meta['count'] + 1):
                    data = out.read(bidx, masked=True)
                    # Burn in any non-fill pixels, and update mask accordingly
                    ne = result != fill
                    data[ne] = result[ne]
                    data.mask[ne] = False
                    out.write(data, indexes=bidx)

        else:
            if like is not None:
                template_ds = rasterio.open(like)

                if has_src_crs and not is_same_crs(src_crs, template_ds.crs):
                    raise click.BadParameter('GeoJSON does not match crs of '
                                             '--like raster',
                                             param='input', param_hint='input')

                if disjoint_bounds(geojson_bounds, template_ds.bounds):
                    click.echo("GeoJSON outside bounds of --like raster. "
                               "Are they in different coordinate reference "
                               "systems?",
                               err=True)

                kwargs = template_ds.meta.copy()
                kwargs['count'] = 1

                # DEPRECATED
                # upgrade transform to affine object or we may get an invalid
                # transform set on output
                kwargs['transform'] = template_ds.transform

                template_ds.close()

            else:
                bounds = bounds or geojson_bounds

                if is_geographic_crs(src_crs):
                    if (bounds[0] < -180 or bounds[2] > 180 or
                            bounds[1] < -80 or bounds[3] > 80):
                        raise click.BadParameter(
                            "Bounds are beyond the valid extent for "
                            "EPSG:4326.",
                            ctx, param=bounds, param_hint='--bounds')

                if dimensions:
                    width, height = dimensions
                    res = (
                        (bounds[2] - bounds[0]) / float(width),
                        (bounds[3] - bounds[1]) / float(height)
                    )

                else:
                    if not res:
                        raise click.BadParameter(
                            'pixel dimensions are required',
                            ctx, param=res, param_hint='--res')

                    elif len(res) == 1:
                        res = (res[0], res[0])

                    width = max(int(ceil((bounds[2] - bounds[0]) /
                                float(res[0]))), 1)
                    height = max(int(ceil((bounds[3] - bounds[1]) /
                                 float(res[1]))), 1)

                src_crs = src_crs.upper()
                if not src_crs.count('EPSG:'):
                    raise click.BadParameter(
                        'invalid CRS.  Must be an EPSG code.',
                        ctx, param=src_crs, param_hint='--src_crs')

                kwargs = {
                    'count': 1,
                    'crs': src_crs,
                    'width': width,
                    'height': height,
                    'transform': Affine(res[0], 0, bounds[0], 0, -res[1],
                                        bounds[3]),
                    'driver': driver
                }
                kwargs.update(**creation_options)

            result = rasterize(
                geometries,
                out_shape=(kwargs['height'], kwargs['width']),
                transform=kwargs.get('affine', kwargs['transform']),
                all_touched=all_touched,
                dtype=kwargs.get('dtype', None),
                default_value=default_value,
                fill=fill)

            if 'dtype' not in kwargs:
                kwargs['dtype'] = result.dtype

            kwargs['nodata'] = fill

            with rasterio.open(output, 'w', **kwargs) as out:
                out.write(result, indexes=1)
