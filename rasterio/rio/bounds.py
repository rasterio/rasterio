import logging
import os

import click
from cligj import (compact_opt, geojson_type_bbox_opt,
                   geojson_type_collection_opt, geojson_type_feature_opt,
                   indent_opt, precision_opt, projection_geographic_opt,
                   projection_mercator_opt, projection_projected_opt,
                   sequence_opt, use_rs_opt)

import rasterio
from rasterio.warp import transform_bounds

from .helpers import to_lower, write_features

logger = logging.getLogger('rio')


# Bounds command.
@click.command(short_help="Write bounding boxes to stdout as GeoJSON.")
# One or more files, the bounds of each are a feature in the collection
# object or feature sequence.
@click.argument('INPUT', nargs=-1, type=click.Path(), required=True)
@precision_opt
@indent_opt
@compact_opt
@projection_geographic_opt
@projection_projected_opt
@projection_mercator_opt
@click.option(
    '--dst-crs', default='', metavar="EPSG:NNNN", callback=to_lower,
    help="Output in specified coordinates.")
@sequence_opt
@use_rs_opt
@geojson_type_collection_opt(True)
@geojson_type_feature_opt(False)
@geojson_type_bbox_opt(False)
@click.pass_context
def bounds(ctx, input, precision, indent, compact, projection, dst_crs,
           sequence, use_rs, geojson_type):
    """Write bounding boxes to stdout as GeoJSON for use with, e.g.,
    geojsonio

      $ rio bounds *.tif | geojsonio

    If a destination crs is passed via dst_crs, it takes precedence over
    the projection parameter.
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

        def __init__(self, env):
            self._xs = []
            self._ys = []
            self.env = env

        @property
        def bbox(self):
            return min(self._xs), min(self._ys), max(self._xs), max(self._ys)

        def __call__(self):
            for i, path in enumerate(input):
                with rasterio.open(path) as src:
                    bounds = src.bounds
                    if dst_crs:
                        bbox = transform_bounds(src.crs,
                                                dst_crs, *bounds)
                    elif projection == 'mercator':
                        bbox = transform_bounds(src.crs,
                                                {'init': 'epsg:3857'}, *bounds)
                    elif projection == 'geographic':
                        bbox = transform_bounds(src.crs,
                                                {'init': 'epsg:4326'}, *bounds)
                    else:
                        bbox = bounds

                if precision >= 0:
                    bbox = [round(b, precision) for b in bbox]

                yield {
                    'type': 'Feature',
                    'bbox': bbox,
                    'geometry': {
                        'type': 'Polygon',
                        'coordinates': [[
                            [bbox[0], bbox[1]],
                            [bbox[2], bbox[1]],
                            [bbox[2], bbox[3]],
                            [bbox[0], bbox[3]],
                            [bbox[0], bbox[1]]]]},
                    'properties': {
                        'id': str(i),
                        'title': path,
                        'filename': os.path.basename(path)}}

                self._xs.extend(bbox[::2])
                self._ys.extend(bbox[1::2])

    try:
        with rasterio.Env(CPL_DEBUG=verbosity > 2) as env:
            write_features(
                stdout, Collection(env), sequence=sequence,
                geojson_type=geojson_type, use_rs=use_rs,
                **dump_kwds)

    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()
