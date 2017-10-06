"""
Helper objects used by multiple CLI commands.
"""


import json
import os

import rasterio
from rasterio.errors import FileOverwriteError


def path_exists(path):

    """Indicates if a path exists.  If ``path`` is a path to a local file on
    disk ``True`` is returned, otherwise Rasterio attempts to open ``path``
    in read-only mode.  If no exceptions are raised then the path is
    assumed to exist.

    Parameters
    ----------
    path : str
        Path (or connection string) to raster.

    Returns
    -------
    bool
    """

    if os.path.exists(path):
        return True

    try:
        with rasterio.open(path):
            return True
    except Exception:
        return False


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


def write_features(
        fobj, collection, sequence=False, geojson_type='feature', use_rs=False,
        **dump_kwds):
    """Read an iterator of (feat, bbox) pairs and write to file using
    the selected modes."""
    # Sequence of features expressed as bbox, feature, or collection.
    if sequence:
        for feat in collection():
            xs, ys = zip(*coords(feat))
            bbox = (min(xs), min(ys), max(xs), max(ys))
            if use_rs:
                fobj.write(u'\u001e')
            if geojson_type == 'feature':
                fobj.write(json.dumps(feat, **dump_kwds))
            elif geojson_type == 'bbox':
                fobj.write(json.dumps(bbox, **dump_kwds))
            else:
                fobj.write(
                    json.dumps({
                        'type': 'FeatureCollection',
                        'bbox': bbox,
                        'features': [feat]}, **dump_kwds))
            fobj.write('\n')
    # Aggregate all features into a single object expressed as
    # bbox or collection.
    else:
        features = list(collection())
        if geojson_type == 'bbox':
            fobj.write(json.dumps(collection.bbox, **dump_kwds))
        elif geojson_type == 'feature':
            fobj.write(json.dumps(features[0], **dump_kwds))
        else:
            fobj.write(json.dumps({
                'bbox': collection.bbox,
                'type': 'FeatureCollection',
                'features': features},
                **dump_kwds))
        fobj.write('\n')


def resolve_inout(input=None, output=None, files=None, force_overwrite=False):
    """Resolves inputs and outputs from standard args and options.

    :param input: a single input filename, optional.
    :param output: a single output filename, optional.
    :param files: a sequence of filenames in which the last is the
        output filename.
    :param force_overwrite: whether to force overwriting the output
        file, bool.
    :return: the resolved output filename and input filenames as a
        tuple of length 2.

    If provided, the :param:`output` file may be overwritten. An output
    file extracted from :param:`files` will not be overwritten unless
    :param:`force_overwrite` is `True`.
    """
    resolved_output = output or (files[-1] if files else None)
    if not force_overwrite and resolved_output \
            and path_exists(resolved_output):
        raise FileOverwriteError(
            "raster exists and won't be overwritten without use of the "
            "'--force-overwrite' option.")
    resolved_inputs = (
        [input] if input else [] +
        list(files[:-1 if not output else None]) if files else [])
    return resolved_output, resolved_inputs


def to_lower(ctx, param, value):
    """Click callback, converts values to lowercase."""
    return value.lower()
