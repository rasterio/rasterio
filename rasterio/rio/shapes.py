import logging
import os

import click
import cligj

from .helpers import coords, write_features
from . import options
import rasterio
from rasterio.transform import Affine

logger = logging.getLogger('rio')


# Common options used below

# Unlike the version in cligj, this one doesn't require values.
files_inout_arg = click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=True),
    metavar="INPUTS... OUTPUT")

all_touched_opt = click.option(
    '-a', '--all', '--all_touched', 'all_touched',
    is_flag=True,
    default=False,
    help='Use all pixels touched by features, otherwise (default) use only '
         'pixels whose center is within the polygon or that are selected by '
         'Bresenhams line algorithm')


@click.command(short_help="Write shapes extracted from bands or masks.")
@options.file_in_arg
@options.output_opt
@cligj.precision_opt
@cligj.indent_opt
@cligj.compact_opt
@cligj.projection_geographic_opt
@cligj.projection_projected_opt
@cligj.sequence_opt
@cligj.use_rs_opt
@cligj.geojson_type_feature_opt(True)
@cligj.geojson_type_bbox_opt(False)
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
                if bidx is not None and bidx > src.count:
                    raise ValueError('bidx is out of range for raster')

                img = None
                msk = None

                # Adjust transforms.
                transform = src.affine
                if sampling > 1:
                    # Decimation of the raster produces a georeferencing
                    # shift that we correct with a translation.
                    transform *= Affine.translation(
                        src.width % sampling, src.height % sampling)
                    # And follow by scaling.
                    transform *= Affine.scale(float(sampling))

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

                    # Possibly overridden below.
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

                src_basename = os.path.basename(src.name)

                # Yield GeoJSON features.
                for i, (g, val) in enumerate(
                        rasterio.features.shapes(img, **kwargs)):
                    if projection == 'geographic':
                        g = rasterio.warp.transform_geom(
                            src.crs, 'EPSG:4326', g,
                            antimeridian_cutting=True, precision=precision)
                    xs, ys = zip(*coords(g))
                    yield {
                        'type': 'Feature',
                        'id': "{0}:{1}".format(src_basename, i),
                        'properties': {
                            'val': val, 'filename': src_basename
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
