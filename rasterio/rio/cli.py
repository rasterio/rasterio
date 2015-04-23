import json
import logging
import sys

import click
from cligj import verbose_opt, quiet_opt

import rasterio


def configure_logging(verbosity):
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)


# The CLI command group.
@click.group(help="Rasterio command line interface.")
@verbose_opt
@quiet_opt
@click.version_option(version=rasterio.__version__, message='%(version)s')
@click.pass_context
def cli(ctx, verbose, quiet):
    verbosity = verbose - quiet
    configure_logging(verbosity)
    ctx.obj = {}
    ctx.obj['verbosity'] = verbosity


# Common arguments and options

# TODO: move file_in_arg and file_out_arg to cligj

# Singular input file
file_in_arg = click.argument(
    'INPUT',
    type=click.Path(exists=True, resolve_path=True))

# Singular output file
file_out_arg = click.argument(
    'OUTPUT',
    type=click.Path(resolve_path=True))

bidx_opt = click.option(
    '-b', '--bidx',
    type=int,
    default=1,
    help="Input file band index (default: 1)")

bidx_mult_opt = click.option(
    '-b', '--bidx',
    multiple=True,
    help="Indexes of input file bands.")

# TODO: may be better suited to cligj
bounds_opt = click.option(
    '--bounds',
    nargs=4, type=float, default=None,
    help='Output bounds: left, bottom, right, top.')

dtype_opt = click.option(
    '-t', '--dtype',
    type=click.Choice([
        'ubyte', 'uint8', 'uint16', 'int16', 'uint32', 'int32',
        'float32', 'float64']),
    default=None,
    help="Output data type (default: float64).")

like_file_opt = click.option(
    '--like',
    type=click.Path(exists=True),
    help='Raster dataset to use as a template for obtaining affine '
         'transform (bounds and resolution), crs, data type, and driver '
         'used to create the output.')

masked_opt = click.option(
    '--masked/--not-masked',
    default=True,
    help="Evaluate expressions using masked arrays (the default) or ordinary "
         "numpy arrays.")

resolution_opt = click.option(
    '-r', '--res',
    multiple=True, type=float, default=None,
    help='Output dataset resolution in units of coordinate '
         'reference system. Pixels assumed to be square if this option '
         'is used once, otherwise use: '
         '--res pixel_width --res pixel_height')

"""
Registry of command line options (also see cligj options):
-a, --all: Use all pixels touched by features.  In rio-mask, rio-rasterize
--as-mask/--not-as-mask: interpret band as mask or not.  In rio-shapes
--band/--mask: use band or mask.  In rio-shapes
--bbox:
-b, --bidx: band index(es) (singular or multiple value versions).  In rio-info, rio-sample, rio-shapes, rio-stack (different usages)
--bounds: bounds in world coordinates.  In rio-info, rio-rasterize (different usages)
--count: count of bands.  In rio-info
--crop: Crop raster to extent of features.  In rio-mask
--crs: CRS of input raster.  In rio-info
--default-value: default for rasterized pixels.  In rio-rasterize
--dimensions: Output width, height.  In rio-rasterize
--dst-crs: destination CRS.  In rio-transform
--fill: fill value for pixels not covered by features.  In rio-rasterize
--formats: list available formats.  In rio-info
--height: height of raster.  In rio-info
-i, --invert: Invert mask created from features: In rio-mask
-j, --geojson-mask: GeoJSON for masking raster.  In rio-mask
--lnglat: geograhpic coordinates of center of raster.  In rio-info
--masked/--not-masked: read masked data from source file.  In rio-calc, rio-info
-m, --mode: output file mode (r, r+).  In rio-insp
--name: input file name alias.  In rio-calc
--nodata: nodata value.  In rio-info, rio-merge (different usages)
--photometric: photometric interpretation.  In rio-stack
--property: GeoJSON property to use as values for rasterize.  In rio-rasterize
-r, --res: output resolution.  In rio-info, rio-rasterize (different usages.  TODO: try to combine usages, prefer rio-rasterize version)
--sampling: Inverse of sampling fraction.  In rio-shapes
--shape: shape (width, height) of band.  In rio-info
--src-crs: source CRS.  In rio-insp, rio-rasterize (different usages.  TODO: consolidate usages)
--stats: print raster stats.  In rio-inf
-t, --dtype: data type.  In rio-calc, rio-info (different usages)
--width: width of raster.  In rio-info
--with-nodata/--without-nodata: include nodata regions or not.  In rio-shapes.
-v, --tell-me-more, --verbose
"""





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
