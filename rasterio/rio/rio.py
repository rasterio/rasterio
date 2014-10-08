#!/usr/bin/env python

"""Rasterio command line interface"""

import functools
import json
import logging
import os.path
import pprint
import sys
import warnings

import click

import rasterio

from rasterio.rio.cli import cli, write_features
from rasterio.rio.bands import stack
from rasterio.rio.info import info
from rasterio.rio.merge import merge
from rasterio.rio.features import shapes


warnings.simplefilter('default')


# Commands are below.
#
# Command bodies less than ~20 lines, e.g. info() below, can go in this
# module. Longer ones, e.g. insp() shall call functions imported from
# rasterio.tool.

# Insp command.
@cli.command(short_help="Open a data file and start an interpreter.")
@click.argument('src_path', type=click.Path(exists=True))
@click.option('--mode', type=click.Choice(['r', 'r+']), default='r', help="File mode (default 'r').")
@click.pass_context
def insp(ctx, src_path, mode):
    import rasterio.tool

    verbosity = ctx.obj['verbosity']
    logger = logging.getLogger('rio')
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            with rasterio.open(src_path, mode) as src:
                rasterio.tool.main(
                    "Rasterio %s Interactive Inspector (Python %s)\n"
                    'Type "src.meta", "src.read_band(1)", or "help(src)" '
                    'for more information.' %  (
                        rasterio.__version__,
                        '.'.join(map(str, sys.version_info[:3]))),
                    src)
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)

# Bounds command.
@cli.command(short_help="Write bounding boxes to stdout as GeoJSON.")

# One or more files, the bounds of each are a feature in the collection
# object or feature sequence.
@click.argument('input', nargs=-1, type=click.Path(exists=True))

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
@click.option('--mercator', 'projected', flag_value='mercator',
              help="Output in Web Mercator coordinates.")

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

@click.pass_context

def bounds(ctx, input, precision, indent, compact, projected, json_mode,
        x_json_seq_rs, output_mode):

    """Write bounding boxes to stdout as GeoJSON for use with, e.g.,
    geojsonio

    $ rio bounds *.tif | geojsonio

    """
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
            for i, path in enumerate(input):
                with rasterio.open(path) as src:
                    bounds = src.bounds
                    xs = [bounds[0], bounds[2]]
                    ys = [bounds[1], bounds[3]]
                    if projected == 'geographic':
                        xs, ys = rasterio.warp.transform(
                            src.crs, {'init': 'epsg:4326'}, xs, ys)
                    if projected == 'mercator':
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
                        'id': str(i), 'title': path} }

                self._xs.extend(bbox[::2])
                self._ys.extend(bbox[1::2])

    collection = Collection()

    # Use the generator defined above as input to the generic output 
    # writing function.
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            write_features(
                stdout, collection, agg_mode=json_mode,
                expression=output_mode, use_rs=x_json_seq_rs,
                **dump_kwds)
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)


# Transform command.
@cli.command(short_help="Transform coordinates.")
@click.argument('input', type=click.File('rb'))
@click.option('--src_crs', default='EPSG:4326', help="Source CRS.")
@click.option('--dst_crs', default='EPSG:4326', help="Destination CRS.")
@click.option('--interleaved', 'mode', flag_value='interleaved', default=True)
@click.option('--precision', type=int, default=-1,
              help="Decimal precision of coordinates.")
@click.pass_context
def transform(ctx, input, src_crs, dst_crs, mode, precision):
    import rasterio.warp

    verbosity = ctx.obj['verbosity']
    logger = logging.getLogger('rio')
    try:
        if mode == 'interleaved':
            coords = json.loads(input.read().decode('utf-8'))
            xs = coords[::2]
            ys = coords[1::2]
        else:
            raise ValueError("Invalid input type '%s'" % input_type)
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
            xs, ys = rasterio.warp.transform(src_crs, dst_crs, xs, ys)
            if precision >= 0:
                xs = [round(v, precision) for v in xs]
                ys = [round(v, precision) for v in ys]
        if mode == 'interleaved':
            result = [0]*len(coords)
            result[::2] = xs
            result[1::2] = ys
        print(json.dumps(result))
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)


if __name__ == '__main__':
    cli()
