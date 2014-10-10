import json
import logging
import sys

import click

import rasterio
from rasterio.rio import options

def configure_logging(verbosity):
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)


# The CLI command group.
@click.group(help="Rasterio command line interface.")
@options.verbose
@options.quiet
@options.version
@click.pass_context
def cli(ctx, verbose, quiet):
    verbosity = verbose - quiet
    configure_logging(verbosity)
    ctx.obj = {}
    ctx.obj['verbosity'] = verbosity


def coords(obj):
    """Yield all coordinate coordinate tuples from a geometry or feature.
    From python-geojson package."""
    if isinstance(obj, (tuple, list)):
        coordinates = obj
    elif 'geometry' in obj:
        coordinates = obj['geometry']['coordinates']
    else:
        coordinates = obj.get('coordinates', obj)
    for e in coordinates:
        if isinstance(e, (float, int)):
            yield tuple(coordinates)
            break
        else:
            for f in coords(e):
                yield f


def write_features(file, collection,
        agg_mode='obj', expression='feature', use_rs=False,
        **dump_kwds):
    """Read an iterator of (feat, bbox) pairs and write to file using
    the selected modes."""
    # Sequence of features expressed as bbox, feature, or collection.
    if agg_mode == 'seq':
        for feat in collection():
            xs, ys = zip(*coords(feat))
            bbox = (min(xs), min(ys), max(xs), max(ys))
            if use_rs:
                file.write(u'\u001e')
            if expression == 'feature':
                file.write(json.dumps(feat, **dump_kwds))
            elif expression == 'bbox':
                file.write(json.dumps(bbox, **dump_kwds))
            else:
                file.write(
                    json.dumps({
                        'type': 'FeatureCollection',
                        'bbox': bbox,
                        'features': [feat]}, **dump_kwds))
            file.write('\n')
    # Aggregate all features into a single object expressed as 
    # bbox or collection.
    else:
        features = list(collection())
        if expression == 'bbox':
            file.write(json.dumps(collection.bbox, **dump_kwds))
        elif expression == 'feature':
            file.write(json.dumps(features[0], **dump_kwds))
        else:
            file.write(json.dumps({
                'bbox': collection.bbox,
                'type': 'FeatureCollection', 
                'features': features},
                **dump_kwds))
        file.write('\n')
