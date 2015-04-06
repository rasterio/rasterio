import functools
import json
import logging
from math import ceil, floor
import os
import sys
import warnings

import click
from cligj import (
    precision_opt, indent_opt, compact_opt, projection_geographic_opt,
    projection_projected_opt, sequence_opt, use_rs_opt,
    geojson_type_feature_opt, geojson_type_bbox_opt, files_inout_arg,
    format_opt)

import rasterio
from rasterio.transform import Affine
from rasterio.rio.cli import cli, coords, write_features


logger = logging.getLogger('rio')
warnings.simplefilter('default')


# Shapes command.
@cli.command(short_help="Write the shapes of features.")
@click.argument('input', type=click.Path(exists=True))
@precision_opt
@indent_opt
@compact_opt
@projection_geographic_opt
@projection_projected_opt
@sequence_opt
@use_rs_opt
@geojson_type_feature_opt(True)
@geojson_type_bbox_opt(False)
@click.option('--band/--mask', default=True,
              help="Extract shapes from one of the dataset bands or from "
                   "its nodata mask")
@click.option('--bidx', 'bandidx', type=int, default=None,
              help="Index of the source band")
@click.option('--sampling', type=int, default=1,
              help="Inverse of the sampling fraction")
@click.option('--with-nodata/--without-nodata', default=False,
              help="Include or do not include (the default) nodata regions.")
@click.option('--as-mask/--not-as-mask', default=False,
              help="Interpret a band as a mask and output only one class of "
                   "valid data shapes.")
@click.pass_context
def shapes(
        ctx, input, precision, indent, compact, projection, sequence,
        use_rs, geojson_type, band, bandidx, sampling, with_nodata, as_mask):
    """Writes features of a dataset out as GeoJSON. It's intended for
    use with single-band rasters and reads from the first band.
    """
    # These import numpy, which we don't want to do unless it's needed.
    import numpy
    import rasterio.features
    import rasterio.warp

    verbosity = ctx.obj['verbosity'] if ctx.obj else 1
    logger = logging.getLogger('rio')
    dump_kwds = {'sort_keys': True}
    if indent:
        dump_kwds['indent'] = indent
    if compact:
        dump_kwds['separators'] = (',', ':')
    stdout = click.get_text_stream('stdout')

    bidx = 1 if bandidx is None and band else bandidx

    # This is the generator for (feature, bbox) pairs.
    class Collection(object):

        def __init__(self):
            self._xs = []
            self._ys = []

        @property
        def bbox(self):
            return min(self._xs), min(self._ys), max(self._xs), max(self._ys)

        def __call__(self):
            with rasterio.open(input) as src:
                img = None
                msk = None
                if band:
                    if sampling == 1:
                        img = src.read(bidx, masked=False)
                        transform = src.affine
                    # Decimate the band.
                    else:
                        img = numpy.zeros(
                            (src.height//sampling, src.width//sampling),
                            dtype=src.dtypes[src.indexes.index(bidx)])
                        img = src.read(bidx, img, masked=False)
                        transform = src.affine * Affine.scale(float(sampling))
                    if as_mask:
                        msk = img
                        img = None
                if not band or not with_nodata:
                    if sampling == 1:
                        msk = src.read_masks(bidx)
                        if bidx is None:
                            msk = numpy.logical_or.reduce(msk).astype('uint8')
                        transform = src.affine
                    # Decimate the mask.
                    else:
                        msk = numpy.zeros(
                            (src.height//sampling, src.width//sampling),
                            dtype=numpy.uint8)
                        msk = src.read_masks(bidx, msk)
                        if bidx is None:
                            msk = numpy.logical_or.reduce(msk)
                        transform = src.affine * Affine.scale(float(sampling))

                bounds = src.bounds
                xs = [bounds[0], bounds[2]]
                ys = [bounds[1], bounds[3]]
                if projection == 'geographic':
                    xs, ys = rasterio.warp.transform(
                        src.crs, {'init': 'epsg:4326'}, xs, ys)
                if precision >= 0:
                    xs = [round(v, precision) for v in xs]
                    ys = [round(v, precision) for v in ys]
                self._xs = xs
                self._ys = ys

                kwargs = {'transform': transform}
                # Default is to exclude nodata features.
                if msk is not None:
                    kwargs['mask'] = (msk>0)
                if img is None:
                    img = msk

                for g, i in rasterio.features.shapes(img, **kwargs):
                    if projection == 'geographic':
                        g = rasterio.warp.transform_geom(
                            src.crs, 'EPSG:4326', g,
                            antimeridian_cutting=True, precision=precision)
                    xs, ys = zip(*coords(g))
                    yield {
                        'type': 'Feature',
                        'id': str(i),
                        'properties': {
                            'val': i, 'filename': os.path.basename(src.name)},
                        'bbox': [min(xs), min(ys), max(xs), max(ys)],
                        'geometry': g }

    if not sequence:
        geojson_type = 'collection'

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            write_features(
                stdout, Collection(), sequence=sequence,
                geojson_type=geojson_type, use_rs=use_rs,
                **dump_kwds)
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)


# Rasterize command.
@cli.command(short_help='Rasterize features.')
@files_inout_arg
@format_opt
@click.option('--like', type=click.Path(exists=True),
              help='Raster dataset to use as a template for obtaining affine '
              'transform (bounds and resolution), crs, data type, and driver '
              'used to create the output.  Only a single band will be output.')
@click.option('--bounds', nargs=4, type=float, default=None,
              help='Output bounds: left, bottom, right, top.')
@click.option('--dimensions', nargs=2, type=int, default=None,
              help='Output dataset width, height in number of pixels.')
@click.option('--res', multiple=True, type=float, default=None,
              help='Output dataset resolution in units of coordinate '
              'reference system. Pixels assumed to be square if this option is '
              'used once, otherwise use: '
              '--res pixel_width --res pixel_height')
@click.option('--src_crs', default='EPSG:4326',
              help='Source coordinate reference system.  Limited to EPSG '
              'codes for now.  Used as output coordinate system if output does '
              'not exist or --like option is not used. Default: EPSG:4326')
@click.option('--all_touched', is_flag=True, default=False)
@click.option('--default_value', type=float, default=1, help='Default value '
              'for rasterized pixels')
@click.option('--fill', type=float, default=0, help='Fill value for all pixels '
              'not overlapping features.  Will be evaluated as NoData pixels '
              'for output.  Default: 0')
@click.option('--property', type=str, default=None, help='Property in '
              'GeoJSON features to use for rasterized values.  Any features '
              'that lack this property will be given --default_value instead.')
@click.pass_context
def rasterize(
        ctx,
        files,
        driver,
        like,
        bounds,
        dimensions,
        res,
        src_crs,
        all_touched,
        default_value,
        fill,
        property):

    """Rasterize GeoJSON into a new or existing raster.

    If the output raster exists, rio-rasterize will rasterize feature values
    into all bands of that raster.  The GeoJSON is assumed to be in the same
    coordinate reference system as the output.

    --default_value or property values when using --property must be using a
    data type valid for the data type of that raster.


    If a template raster is provided using the --like option, the affine
    transform, coordinate reference system, and data type from that raster will
    be used to create the output.

    --default_value or property values when using --property must be using a
    data type valid for the data type of that raster.

    --driver, --bounds, --dimensions, --res, and --src_crs are ignored when
    output exists or --like raster is provided

    The GeoJSON must be within the bounds of the existing output or --like
    raster, or an error will be raised.


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

    import numpy as np
    from rasterio.features import rasterize
    from rasterio.features import bounds as calculate_bounds

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1

    files = list(files)
    output = files.pop()
    input = click.open_file(files.pop(0) if files else '-')

    # If values are actually meant to be integers, we need to cast them
    # as such or rasterize creates floating point outputs
    if default_value == int(default_value):
        default_value = int(default_value)
    if fill == int(fill):
        fill = int(fill)

    with rasterio.drivers(CPL_DEBUG=verbosity > 2):

        def feature_value(feature):
            if property and 'properties' in feature:
                return feature['properties'].get(property, default_value)
            return default_value

        def disjoint_bounds(bounds1, bounds2):
            return (bounds1[0] > bounds2[2] or
                    bounds1[2] < bounds2[0] or
                    bounds1[1] > bounds2[3] or
                    bounds1[3] < bounds2[1])

        geojson = json.loads(input.read())
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
                if disjoint_bounds(geojson_bounds, out.bounds):
                    raise click.BadParameter('GeoJSON outside bounds of '
                                             'existing output raster',
                                             param=input, param_hint='input')

                meta = out.meta.copy()

                result = rasterize(
                    geometries,
                    out_shape=(meta['height'], meta['width']),
                    transform=meta.get('affine', meta['transform']),
                    all_touched=all_touched,
                    dtype=meta.get('dtype', None),
                    default_value=default_value,
                    fill = fill)

                for bidx in range(1, meta['count'] + 1):
                    data = out.read_band(bidx, masked=True)
                    # Burn in any non-fill pixels, and update mask accordingly
                    ne = result != fill
                    data[ne] = result[ne]
                    data.mask[ne] = False
                    out.write_band(bidx, data)

        else:
            if like is not None:
                template_ds = rasterio.open(like)
                if disjoint_bounds(geojson_bounds, template_ds.bounds):
                    raise click.BadParameter('GeoJSON outside bounds of '
                                             '--like raster', param=input,
                                             param_hint='input')

                kwargs = template_ds.meta.copy()
                kwargs['count'] = 1
                template_ds.close()

            else:
                bounds = bounds or geojson_bounds

                if src_crs == 'EPSG:4326':
                    if (bounds[0] < -180 or bounds[2] > 180 or
                        bounds[1] < -80 or bounds[3] > 80):
                        raise click.BadParameter(
                            'Bounds are beyond the valid extent for EPSG:4326.',
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

            result = rasterize(
                geometries,
                out_shape=(kwargs['height'], kwargs['width']),
                transform=kwargs.get('affine', kwargs['transform']),
                all_touched=all_touched,
                dtype=kwargs.get('dtype', None),
                default_value=default_value,
                fill = fill)

            if 'dtype' not in kwargs:
                kwargs['dtype'] = result.dtype

            kwargs['nodata'] = fill

            with rasterio.open(output, 'w', **kwargs) as out:
                out.write_band(1, result)
