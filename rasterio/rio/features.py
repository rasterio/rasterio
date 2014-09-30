import functools
import json
import logging
import sys
import warnings

import click

import rasterio
from rasterio.transform import Affine
from rasterio.rio.cli import cli, coords, write_features


warnings.simplefilter('default')


def transform_geom(transformer, g, precision=-1):
    if g['type'] == 'Point':
        x, y = g['coordinates']
        xp, yp = transformer([x], [y])
        if precision >= 0:
            xp = [round(v, precision) for v in xp]
            yp = [round(v, precision) for v in yp]
        new_coords = list(zip(xp, yp))[0]
    if g['type'] in ['LineString', 'MultiPoint']:
        xp, yp = transformer(*zip(g['coordinates']))
        if precision >= 0:
            xp = [round(v, precision) for v in xp]
            yp = [round(v, precision) for v in yp]
        new_coords = list(zip(xp, yp))
    elif g['type'] in ['Polygon', 'MultiLineString']:
        new_coords = []
        for piece in g['coordinates']:
            xp, yp = transformer(*zip(*piece))
            if precision >= 0:
                xp = [round(v, precision) for v in xp]
                yp = [round(v, precision) for v in yp]
            new_coords.append(list(zip(xp, yp)))
    elif g['type'] == 'MultiPolygon':
        parts = g['coordinates']
        new_coords = []
        for part in parts:
            inner_coords = []
            for ring in part:
                xp, yp = transformer(*zip(*ring))
                if precision >= 0:
                    xp = [round(v, precision) for v in xp]
                    yp = [round(v, precision) for v in yp]
                inner_coords.append(list(zip(xp, yp)))
            new_coords.append(inner_coords)
    g['coordinates'] = new_coords
    return g


# Shapes command.
@cli.command(short_help="Write the shapes of features.")
@click.argument('input', type=click.Path(exists=True))
# Coordinate precision option.
@click.option('--precision', type=int, default=-1,
              help="Decimal precision of coordinates.")
# JSON formatting options.
@click.option('--indent', default=None, type=int,
              help="Indentation level for JSON output")
@click.option('--compact/--no-compact', default=False,
              help="Use compact separators (',', ':').")
# Geographic (default) or Mercator switch.
@click.option('--geographic', 'projected', flag_value='geographic',
              default=True,
              help="Output in geographic coordinates (the default).")
@click.option('--projected', 'projected', flag_value='projected',
              help="Output in projected coordinates.")
# JSON object (default) or sequence (experimental) switch.
@click.option('--json-obj', 'json_mode', flag_value='obj', default=True,
        help="Write a single JSON object (the default).")
@click.option('--x-json-seq', 'json_mode', flag_value='seq',
        help="Write a JSON sequence. Experimental.")
# Use ASCII RS control code to signal a sequence item (False is default).
# See http://tools.ietf.org/html/draft-ietf-json-text-sequence-05.
# Experimental.
@click.option('--x-json-seq-rs/--x-json-seq-no-rs', default=False,
        help="Use RS as text separator. Experimental.")
# GeoJSON feature (default), bbox, or collection switch. Meaningful only
# when --x-json-seq is used.
@click.option('--collection', 'output_mode', flag_value='collection',
              default=True,
              help="Output as a GeoJSON feature collection (the default).")
@click.option('--feature', 'output_mode', flag_value='feature',
              help="Output as sequence of GeoJSON features.")
@click.option('--bbox', 'output_mode', flag_value='bbox',
              help="Output as a GeoJSON bounding box array.")
@click.option('--bands/--mask', default=True,
              help="Extract shapes from one of the dataset bands or from "
                   "its nodata mask")
@click.option('--bidx', type=int, default=1,
              help="Index of the source band")
@click.option('--sampling', type=int, default=1,
              help="Inverse of the sampling fraction")
@click.option('--with-nodata/--without-nodata', default=False,
              help="Include or do not include (the default) nodata regions.")
@click.pass_context
def shapes(
        ctx, input, precision, indent, compact, projected, json_mode,
        x_json_seq_rs, output_mode, bands, bidx, sampling, with_nodata):
    """Writes features of a dataset out as GeoJSON. It's intended for
    use with single-band rasters and reads from the first band.
    """
    # These import numpy, which we don't want to do unless its needed.
    import numpy
    import rasterio.features
    import rasterio.warp

    verbosity = ctx.obj['verbosity']
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
            with rasterio.open(input) as src:
                if bands:
                    if sampling == 1:
                        img = src.read_band(bidx)
                        transform = src.transform
                    # Decimate the band.
                    else:
                        img = numpy.zeros(
                            (src.height//sampling, src.width//sampling),
                            dtype=src.dtypes[src.indexes.index(bidx)])
                        img = src.read_band(bidx, img)
                        transform = src.affine * Affine.scale(float(sampling))
                else:
                    if sampling == 1:
                        img = src.read_mask()
                        transform = src.transform
                    # Decimate the mask.
                    else:
                        img = numpy.zeros(
                            (src.height//sampling, src.width//sampling),
                            dtype=numpy.uint8)
                        img = src.read_mask(img)
                        transform = src.affine * Affine.scale(float(sampling))

                bounds = src.bounds
                xs = [bounds[0], bounds[2]]
                ys = [bounds[1], bounds[3]]
                if projected == 'geographic':
                    xs, ys = rasterio.warp.transform(
                        src.crs, {'init': 'epsg:4326'}, xs, ys)
                if precision >= 0:
                    xs = [round(v, precision) for v in xs]
                    ys = [round(v, precision) for v in ys]
                self._xs = xs
                self._ys = ys

                # To be used in the geographic case below.
                transformer = functools.partial(
                                rasterio.warp.transform,
                                src.crs,
                                {'init': 'epsg:4326'})
                
                kwargs = {'transform': transform}
                if not bands and not with_nodata:
                    kwargs['mask'] = (img==255)
                for g, i in rasterio.features.shapes(img, **kwargs):
                    if projected == 'geographic':
                        g = transform_geom(transformer, g, precision)
                    xs, ys = zip(*coords(g))
                    yield {
                        'type': 'Feature',
                        'id': str(i),
                        'properties': {'val': i},
                        'bbox': [min(xs), min(ys), max(xs), max(ys)],
                        'geometry': g }

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            write_features(
                stdout, Collection(), agg_mode=json_mode,
                expression=output_mode, use_rs=x_json_seq_rs,
                **dump_kwds)
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
