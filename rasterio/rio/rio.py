"""Rasterio command line interface"""

import functools
import json
import logging
import os.path
import pprint
import sys
import warnings

import click
from cligj import (
    precision_opt, indent_opt, compact_opt, projection_geographic_opt,
    projection_projected_opt, projection_mercator_opt,
    sequence_opt, use_rs_opt, geojson_type_collection_opt,
    geojson_type_feature_opt, geojson_type_bbox_opt)

import rasterio
from rasterio.rio.cli import cli, write_features, file_in_arg


warnings.simplefilter('default')


# Commands are below.
#
# Command bodies less than ~20 lines, e.g. info() below, can go in this
# module. Longer ones, e.g. insp() shall call functions imported from
# rasterio.tool.

# Insp command.
@cli.command(short_help="Open a data file and start an interpreter.")
@file_in_arg
@click.option(
    '--ipython/--no-ipython',
    default=True,
    help='Use IPython as interpreter.')
@click.option(
    '-m',
    '--mode',
    type=click.Choice(['r', 'r+']),
    default='r',
    help="File mode (default 'r').")
@click.pass_context
def insp(ctx, input, mode, ipython):
    import rasterio.tool
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            with rasterio.open(input, mode) as src:
                rasterio.tool.main(
                    "Rasterio %s Interactive Inspector (Python %s)\n"
                    'Type "src.meta", "src.read_band(1)", or "help(src)" '
                    'for more information.' %  (
                        rasterio.__version__,
                        '.'.join(map(str, sys.version_info[:3]))),
                    src, ipython)
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()


# Bounds command.
@cli.command(short_help="Write bounding boxes to stdout as GeoJSON.")
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


# Transform command.
@cli.command(short_help="Transform coordinates.")
@click.argument('INPUT', default='-', required=False)
@click.option('--src-crs', '--src_crs', default='EPSG:4326', help="Source CRS.")
@click.option('--dst-crs', '--dst_crs', default='EPSG:4326', help="Destination CRS.")
@precision_opt
@click.pass_context
def transform(ctx, input, src_crs, dst_crs, precision):
    import rasterio.warp

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    # Handle the case of file, stream, or string input.
    try:
        src = click.open_file(input).readlines()
    except IOError:
        src = [input]

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            if src_crs.startswith('EPSG'):
                src_crs = {'init': src_crs}
            elif os.path.exists(src_crs):
                with rasterio.open(src_crs) as f:
                    src_crs = f.crs
            if dst_crs.startswith('EPSG'):
                dst_crs = {'init': dst_crs}
            elif os.path.exists(dst_crs):
                with rasterio.open(dst_crs) as f:
                    dst_crs = f.crs
            for line in src:
                coords = json.loads(line)
                xs = coords[::2]
                ys = coords[1::2]
                xs, ys = rasterio.warp.transform(src_crs, dst_crs, xs, ys)
                if precision >= 0:
                    xs = [round(v, precision) for v in xs]
                    ys = [round(v, precision) for v in ys]
                result = [0]*len(coords)
                result[::2] = xs
                result[1::2] = ys
                print(json.dumps(result))

    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()
