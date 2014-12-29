import functools
import json
import logging
import sys
import warnings

import click
from cligj import (
    precision_opt, indent_opt, compact_opt, projection_geographic_opt,
    projection_projected_opt, sequence_opt, use_rs_opt,
    geojson_type_feature_opt, geojson_type_bbox_opt)

import rasterio
from rasterio.transform import Affine
from rasterio.rio.cli import cli, coords, write_features


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
        ctx, input, precision, indent, compact, projection, sequence,
        use_rs, geojson_type, bands, bidx, sampling, with_nodata):
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
                if projection == 'geographic':
                    xs, ys = rasterio.warp.transform(
                        src.crs, {'init': 'epsg:4326'}, xs, ys)
                if precision >= 0:
                    xs = [round(v, precision) for v in xs]
                    ys = [round(v, precision) for v in ys]
                self._xs = xs
                self._ys = ys

                kwargs = {'transform': transform}
                if not bands and not with_nodata:
                    kwargs['mask'] = (img==255)
                for g, i in rasterio.features.shapes(img, **kwargs):
                    if projection == 'geographic':
                        g = rasterio.warp.transform_geom(
                            src.crs, 'EPSG:4326', g,
                            antimeridian_cutting=True, precision=precision)
                    xs, ys = zip(*coords(g))
                    yield {
                        'type': 'Feature',
                        'id': str(i),
                        'properties': {'val': i},
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
