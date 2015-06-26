import json
import logging
from math import ceil
import os
import shutil

import click
import cligj
from cligj import (
    precision_opt, indent_opt, compact_opt, projection_geographic_opt,
    projection_mercator_opt, projection_projected_opt, sequence_opt,
    use_rs_opt, geojson_type_feature_opt, geojson_type_bbox_opt,
    files_inout_arg, format_opt, geojson_type_collection_opt)

from .helpers import coords, resolve_inout, write_features
from . import options
import rasterio
from rasterio.transform import Affine
import rasterio.warp
from rasterio.coords import BoundingBox


logger = logging.getLogger('rio')


# Common options used below
all_touched_opt = click.option(
    '-a', '--all', '--all_touched', 'all_touched',
    is_flag=True,
    default=False,
    help='Use all pixels touched by features, otherwise (default) use only '
         'pixels whose center is within the polygon or that are selected by '
         'Bresenhams line algorithm')


# Mask command
@click.command(short_help='Mask in raster using features.')
@cligj.files_inout_arg
@options.output_opt
@click.option('-j', '--geojson-mask', 'geojson_mask',
              type=click.Path(), default=None,
              help='GeoJSON file to use for masking raster.  Use "-" to read '
                   'from stdin.  If not provided, original raster will be '
                   'returned')
@format_opt
@all_touched_opt
@click.option('--crop', is_flag=True, default=False,
              help='Crop output raster to the extent of the geometries. '
                   'GeoJSON must overlap input raster to use --crop')
@click.option('-i', '--invert', is_flag=True, default=False,
              help='Inverts the mask, so that areas covered by features are'
                   'masked out and areas not covered are retained.  Ignored '
                   'if using --crop')
@click.pass_context
def mask(
        ctx,
        files,
        output,
        geojson_mask,
        driver,
        all_touched,
        crop,
        invert):

    """Masks in raster using GeoJSON features (masks out all areas not covered
    by features), and optionally crops the output raster to the extent of the
    features.

    GeoJSON must be the first input file or provided from stdin:

    > rio mask input.tif output.tif --geojson-mask features.json

    > rio mask input.tif output.tif --geojson-mask - < features.json

    If the output raster exists, it will be completely overwritten with the
    results of this operation.

    The result is always equal to or within the bounds of the input raster.

    --crop and --invert options are mutually exclusive.

    --crop option is not valid if features are completely outside extent of
    input raster.
    """

    from rasterio.features import geometry_mask
    from rasterio.features import bounds as calculate_bounds

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1

    output, files = resolve_inout(files=files, output=output)
    input = files[0]

    if geojson_mask is None:
        click.echo('No GeoJSON provided, INPUT will be copied to OUTPUT',
                   err=True)
        shutil.copy(input, output)
        return

    if crop and invert:
        click.echo('Invert option ignored when using --crop', err=True)
        invert = False

    with rasterio.drivers(CPL_DEBUG=verbosity > 2):
        try:
            geojson = json.loads(click.open_file(geojson_mask).read())
        except ValueError:
            raise click.BadParameter('GeoJSON could not be read from  '
                                     '--geojson-mask or stdin',
                                     param_hint='--geojson-mask')

        if 'features' in geojson:
            geometries = (f['geometry'] for f in geojson['features'])
        elif 'geometry' in geojson:
            geometries = (geojson['geometry'], )
        else:
            raise click.BadParameter('Invalid GeoJSON', param=input,
                                     param_hint='input')
        bounds = geojson.get('bbox', calculate_bounds(geojson))

        with rasterio.open(input) as src:
            
            # Determine the projection of the GeoJSON mask
            if geojson.get('crs', {}).get('type') == 'name':
                from_crs = geojson.get('crs').get('properties').get('name')
            else:
                from_crs = {'init': 'epsg:4326'}
            
            # Transform input bounds and geometries to the src projection
            x, y = bounds[0::2], bounds[1::2]
            (left, right), (bottom, top) = rasterio.warp.transform(from_crs, src.crs, x, y)
            bounds = BoundingBox(left, bottom, right, top)
            
            geometries = map(lambda g: rasterio.warp.transform_geom(from_crs, src.crs, g), geometries)
            
            disjoint_bounds = _disjoint_bounds(bounds, src.bounds)

            if crop:
                if disjoint_bounds:
                    raise click.BadParameter('not allowed for GeoJSON outside '
                                             'the extent of the input raster',
                                             param=crop, param_hint='--crop')

                window = src.window(*bounds)
                transform = src.window_transform(window)
                (r1, r2), (c1, c2) = window
                mask_shape = (r2 - r1, c2 - c1)
            else:
                if disjoint_bounds:
                    click.echo('GeoJSON outside bounds of existing output '
                               'raster.',
                               err=True)

                window = None
                transform = src.affine
                mask_shape = src.shape

            mask = geometry_mask(
                geometries,
                out_shape=mask_shape,
                transform=transform,
                all_touched=all_touched,
                invert=invert)

            meta = src.meta.copy()
            meta.update({
                'driver': driver,
                'height': mask.shape[0],
                'width': mask.shape[1],
                'transform': transform
            })

            with rasterio.open(output, 'w', **meta) as out:
                for bidx in range(1, src.count + 1):
                    img = src.read(bidx, masked=True, window=window)
                    img.mask = img.mask | mask
                    out.write_band(bidx, img.filled(src.nodatavals[bidx-1]))


# Shapes command.
@click.command(short_help="Write shapes extracted from bands or masks.")
@click.argument('input', type=click.Path(exists=True))
@options.output_opt
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
              help="Choose to extract from a band (the default) or a mask.")
@click.option('--bidx', 'bandidx', type=int, default=None,
              help="Index of the band or mask that is the source of shapes.")
@click.option('--sampling', type=int, default=1,
              help="Inverse of the sampling fraction; "
                   "a value of 10 decimates.")
@click.option('--with-nodata/--without-nodata', default=False,
              help="Include or do not include (the default) nodata regions.")
@click.option('--as-mask/--not-as-mask', default=False,
              help="Interpret a band as a mask and output only one class of "
                   "valid data shapes.")
@click.pass_context
def shapes(
        ctx, input, output, precision, indent, compact, projection, sequence,
        use_rs, geojson_type, band, bandidx, sampling, with_nodata, as_mask):
    """Extracts shapes from one band or mask of a dataset and writes
    them out as GeoJSON. Unless otherwise specified, the shapes will be
    transformed to WGS 84 coordinates.

    The default action of this command is to extract shapes from the
    first band of the input dataset. The shapes are polygons bounding
    contiguous regions (or features) of the same raster value. This
    command performs poorly for int16 or float type datasets.

    Bands other than the first can be specified using the `--bidx`
    option:

      $ rio shapes --bidx 3 tests/data/RGB.byte.tif

    The valid data footprint of a dataset's i-th band can be extracted
    by using the `--mask` and `--bidx` options:

      $ rio shapes --mask --bidx 1 tests/data/RGB.byte.tif

    Omitting the `--bidx` option results in a footprint extracted from
    the conjunction of all band masks. This is generally smaller than
    any individual band's footprint.

    A dataset band may be analyzed as though it were a binary mask with
    the `--as-mask` option:

      $ rio shapes --as-mask --bidx 1 tests/data/RGB.byte.tif
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

    stdout = click.open_file(
        output, 'w') if output else click.get_text_stream('stdout')

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

                # Adjust transforms.
                if sampling == 1:
                    transform = src.affine
                else:
                    transform = src.affine * Affine.scale(float(sampling))

                # Most of the time, we'll use the valid data mask.
                # We skip reading it if we're extracting every possible
                # feature (even invalid data features) from a band.
                if not band or (band and not as_mask and not with_nodata):
                    if sampling == 1:
                        msk = src.read_masks(bidx)
                    else:
                        msk_shape = (
                            src.height//sampling, src.width//sampling)
                        if bidx is None:
                            msk = numpy.zeros(
                                (src.count,) + msk_shape, 'uint8')
                        else:
                            msk = numpy.zeros(msk_shape, 'uint8')
                        msk = src.read_masks(bidx, msk)

                    if bidx is None:
                        msk = numpy.logical_or.reduce(msk).astype('uint8')

                    # Possibly overidden below.
                    img = msk

                # Read the band data unless the --mask option is given.
                if band:
                    if sampling == 1:
                        img = src.read(bidx, masked=False)
                    else:
                        img = numpy.zeros(
                            (src.height//sampling, src.width//sampling),
                            dtype=src.dtypes[src.indexes.index(bidx)])
                        img = src.read(bidx, img, masked=False)

                # If --as-mask option was given, convert the image
                # to a binary image. This reduces the number of shape
                # categories to 2 and likely reduces the number of
                # shapes.
                if as_mask:
                    tmp = numpy.ones_like(img, 'uint8') * 255
                    tmp[img == 0] = 0
                    img = tmp
                    if not with_nodata:
                        msk = tmp

                # Transform the raster bounds.
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

                # Prepare keyword arguments for shapes().
                kwargs = {'transform': transform}
                if not with_nodata:
                    kwargs['mask'] = msk

                # Yield GeoJSON features.
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
                            'val': i, 'filename': os.path.basename(src.name)
                        },
                        'bbox': [min(xs), min(ys), max(xs), max(ys)],
                        'geometry': g
                    }

    if not sequence:
        geojson_type = 'collection'

    try:
        with rasterio.drivers(CPL_DEBUG=(verbosity > 2)):
            write_features(
                stdout, Collection(), sequence=sequence,
                geojson_type=geojson_type, use_rs=use_rs,
                **dump_kwds)
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()


# Rasterize command.
@click.command(short_help='Rasterize features.')
@files_inout_arg
@options.output_opt
@format_opt
@options.like_file_opt
@options.bounds_opt
@click.option('--dimensions', nargs=2, type=int, default=None,
              help='Output dataset width, height in number of pixels.')
@options.resolution_opt
@click.option('--src-crs', '--src_crs', 'src_crs', default=None,
              help='Source coordinate reference system.  Limited to EPSG '
              'codes for now.  Used as output coordinate system if output '
              'does not exist or --like option is not used. '
              'Default: EPSG:4326')
@all_touched_opt
@click.option('--default-value', '--default_value', 'default_value',
              type=float, default=1, help='Default value for rasterized pixels')
@click.option('--fill', type=float, default=0,
              help='Fill value for all pixels not overlapping features.  Will '
              'be evaluated as NoData pixels for output.  Default: 0')
@click.option('--property', type=str, default=None, help='Property in '
              'GeoJSON features to use for rasterized values.  Any features '
              'that lack this property will be given --default_value instead.')
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
        property):

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

    output, files = resolve_inout(files=files, output=output)
    input = click.open_file(files.pop(0) if files else '-')

    has_src_crs = src_crs is not None
    src_crs = src_crs or 'EPSG:4326'

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
                if has_src_crs and not is_same_crs(src_crs, out.crs):
                    raise click.BadParameter('GeoJSON does not match crs of '
                                             'existing output raster',
                                             param='input', param_hint='input')

                if _disjoint_bounds(geojson_bounds, out.bounds):
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

                if has_src_crs and not is_same_crs(src_crs, template_ds.crs):
                    raise click.BadParameter('GeoJSON does not match crs of '
                                             '--like raster',
                                             param='input', param_hint='input')

                if _disjoint_bounds(geojson_bounds, template_ds.bounds):
                    click.echo("GeoJSON outside bounds of --like raster. "
                               "Are they in different coordinate reference "
                               "systems?",
                               err=True)

                kwargs = template_ds.meta.copy()
                kwargs['count'] = 1
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


# Bounds command.
@click.command(short_help="Write bounding boxes to stdout as GeoJSON.")
# One or more files, the bounds of each are a feature in the collection
# object or feature sequence.
@click.argument('INPUT', nargs=-1, type=click.Path(exists=True))
@precision_opt
@indent_opt
@compact_opt
@projection_geographic_opt
@projection_projected_opt
@projection_mercator_opt
@sequence_opt
@use_rs_opt
@geojson_type_collection_opt(True)
@geojson_type_feature_opt(False)
@geojson_type_bbox_opt(False)
@click.pass_context
def bounds(ctx, input, precision, indent, compact, projection, sequence,
        use_rs, geojson_type):
    """Write bounding boxes to stdout as GeoJSON for use with, e.g.,
    geojsonio

      $ rio bounds *.tif | geojsonio

    """
    import rasterio.warp
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')
    dump_kwds = {'sort_keys': True}
    if indent:
        dump_kwds['indent'] = indent
    if compact:
        dump_kwds['separators'] = (',', ':')
    stdout = click.get_text_stream('stdout')

    # This is the generator for (feature, bbox) pairs.
    class Collection(object):

        def __init__(self):
            self._xs = []
            self._ys = []

        @property
        def bbox(self):
            return min(self._xs), min(self._ys), max(self._xs), max(self._ys)

        def __call__(self):
            for i, path in enumerate(input):
                with rasterio.open(path) as src:
                    bounds = src.bounds
                    xs = [bounds[0], bounds[2]]
                    ys = [bounds[1], bounds[3]]
                    if projection == 'geographic':
                        xs, ys = rasterio.warp.transform(
                            src.crs, {'init': 'epsg:4326'}, xs, ys)
                    if projection == 'mercator':
                        xs, ys = rasterio.warp.transform(
                            src.crs, {'init': 'epsg:3857'}, xs, ys)
                if precision >= 0:
                    xs = [round(v, precision) for v in xs]
                    ys = [round(v, precision) for v in ys]
                bbox = [min(xs), min(ys), max(xs), max(ys)]

                yield {
                    'type': 'Feature',
                    'bbox': bbox,
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [xs[0], ys[0]],
                            [xs[1], ys[0]],
                            [xs[1], ys[1]],
                            [xs[0], ys[1]],
                            [xs[0], ys[0]] ]]},
                    'properties': {
                        'id': str(i),
                        'title': path,
                        'filename': os.path.basename(path)} }

                self._xs.extend(bbox[::2])
                self._ys.extend(bbox[1::2])

    col = Collection()
    # Use the generator defined above as input to the generic output
    # writing function.
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            write_features(
                stdout, col, sequence=sequence,
                geojson_type=geojson_type, use_rs=use_rs,
                **dump_kwds)

    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()


def _disjoint_bounds(bounds1, bounds2):
    return (bounds1[0] > bounds2[2] or bounds1[2] < bounds2[0] or
            bounds1[1] > bounds2[3] or bounds1[3] < bounds2[1])
