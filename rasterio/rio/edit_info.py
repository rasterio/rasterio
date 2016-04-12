"""Fetch and edit raster dataset metadata from the command line."""

import json
import logging

import click

from . import options
import rasterio
import rasterio.crs
from rasterio.env import Env
from rasterio.transform import guard_transform


# Handlers for info module options.

def all_handler(ctx, param, value):
    """Get tags from a template file or command line."""
    if ctx.obj and ctx.obj.get('like') and value is not None:
        ctx.obj['all_like'] = value
        value = ctx.obj.get('like')
    return value


def crs_handler(ctx, param, value):
    """Get crs value from a template file or command line."""
    retval = options.from_like_context(ctx, param, value)
    if retval is None and value:
        try:
            retval = json.loads(value)
        except ValueError:
            retval = value
        if not rasterio.crs.is_valid_crs(retval):
            raise click.BadParameter(
                "'%s' is not a recognized CRS." % retval,
                param=param, param_hint='crs')
    return retval


def tags_handler(ctx, param, value):
    """Get tags from a template file or command line."""
    retval = options.from_like_context(ctx, param, value)
    if retval is None and value:
        try:
            retval = dict(p.split('=') for p in value)
        except:
            raise click.BadParameter(
                "'%s' contains a malformed tag." % value,
                param=param, param_hint='transform')
    return retval


def transform_handler(ctx, param, value):
    """Get transform value from a template file or command line."""
    retval = options.from_like_context(ctx, param, value)
    if retval is None and value:
        try:
            value = json.loads(value)
        except ValueError:
            pass
        try:
            retval = guard_transform(value)
        except:
            raise click.BadParameter(
                "'%s' is not recognized as an Affine or GDAL "
                "geotransform array." % value,
                param=param, param_hint='transform')
    return retval


# The edit-info command.

@click.command('edit-info', short_help="Edit dataset metadata.")
@options.file_in_arg
@options.nodata_opt
@click.option('--crs', callback=crs_handler, default=None,
              help="New coordinate reference system")
@click.option('--transform', callback=transform_handler,
              help="New affine transform matrix")
@click.option('--tag', 'tags', callback=tags_handler, multiple=True,
              metavar='KEY=VAL', help="New tag.")
@click.option('--all', 'allmd', callback=all_handler, flag_value='like',
              is_eager=True, default=False,
              help="Copy all metadata items from the template file.")
@options.like_opt
@click.pass_context
def edit(ctx, input, nodata, crs, transform, tags, allmd, like):
    """Edit a dataset's metadata: coordinate reference system, affine
    transformation matrix, nodata value, and tags.

    The coordinate reference system may be either a PROJ.4 or EPSG:nnnn
    string,

      --crs 'EPSG:4326'

    or a JSON text-encoded PROJ.4 object.

      --crs '{"proj": "utm", "zone": 18, ...}'

    Transforms are either JSON-encoded Affine objects (preferred),

      --transform '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'

    or JSON text-encoded GDAL geotransform arrays.

      --transform '[101985.0, 300.038, 0.0, 2826915.0, 0.0, -300.042]'

    Metadata items may also be read from an existing dataset using a
    combination of the --like option with at least one of --all,
    `--crs like`, `--nodata like`, and `--transform like`.

      rio edit-info example.tif --like template.tif --all

    To get just the transform from the template:

      rio edit-info example.tif --like template.tif --transform like

    """
    import numpy as np

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1

    def in_dtype_range(value, dtype):
        infos = {'c': np.finfo, 'f': np.finfo, 'i': np.iinfo,
                 'u': np.iinfo}
        rng = infos[np.dtype(dtype).kind](dtype)
        return rng.min <= value <= rng.max

    with Env(CPL_DEBUG=(verbosity > 2)) as env:

        with rasterio.open(input, 'r+') as dst:

            if allmd:
                nodata = allmd['nodata']
                crs = allmd['crs']
                transform = allmd['transform']
                tags = allmd['tags']

            if nodata is not None:
                dtype = dst.dtypes[0]
                if not in_dtype_range(nodata, dtype):
                    raise click.BadParameter(
                        "outside the range of the file's "
                        "data type (%s)." % dtype,
                        param=nodata, param_hint='nodata')
                dst.nodata = nodata

            if crs:
                dst.crs = crs

            if transform:
                dst.transform = transform

            if tags:
                dst.update_tags(**tags)
