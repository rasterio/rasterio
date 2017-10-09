"""Fetch and edit raster dataset metadata from the command line."""


import json
import warnings

import click

import rasterio
import rasterio.crs
from rasterio.crs import CRS
from rasterio.errors import CRSError
from rasterio.rio import options
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
        try:
            if isinstance(retval, dict):
                retval = CRS(retval)
            else:
                retval = CRS.from_string(retval)
        except CRSError:
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
                "'%s' is not recognized as an Affine array." % value,
                param=param, param_hint='transform')
    return retval


@click.command('edit-info', short_help="Edit dataset metadata.")
@options.file_in_arg
@options.bidx_opt
@options.edit_nodata_opt
@click.option('--unset-nodata', default=False, is_flag=True,
              help="Unset the dataset's nodata value.")
@click.option('--crs', callback=crs_handler, default=None,
              help="New coordinate reference system")
@click.option('--unset-crs', default=False, is_flag=True,
              help="Unset the dataset's CRS value.")
@click.option('--transform', callback=transform_handler,
              help="New affine transform matrix")
@click.option('--units', help="Edit units of a band (requires --bidx)")
@click.option('--description',
              help="Edit description of a band (requires --bidx)")
@click.option('--tag', 'tags', callback=tags_handler, multiple=True,
              metavar='KEY=VAL', help="New tag.")
@click.option('--all', 'allmd', callback=all_handler, flag_value='like',
              is_eager=True, default=False,
              help="Copy all metadata items from the template file.")
@options.like_opt
@click.pass_context
def edit(ctx, input, bidx, nodata, unset_nodata, crs, unset_crs, transform,
         units, description, tags, allmd, like):
    """Edit a dataset's metadata: coordinate reference system, affine
    transformation matrix, nodata value, and tags.

    The coordinate reference system may be either a PROJ.4 or EPSG:nnnn
    string,

      --crs 'EPSG:4326'

    or a JSON text-encoded PROJ.4 object.

      --crs '{"proj": "utm", "zone": 18, ...}'

    Transforms are JSON-encoded Affine objects like:

      --transform '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'

    Prior to Rasterio 1.0 GDAL geotransforms were supported for --transform,
    but are no longer supported.

    Metadata items may also be read from an existing dataset using a
    combination of the --like option with at least one of --all,
    `--crs like`, `--nodata like`, and `--transform like`.

      rio edit-info example.tif --like template.tif --all

    To get just the transform from the template:

      rio edit-info example.tif --like template.tif --transform like

    """
    import numpy as np

    def in_dtype_range(value, dtype):
        kind = np.dtype(dtype).kind
        if kind == 'f' and np.isnan(value):
            return True
        infos = {'c': np.finfo, 'f': np.finfo, 'i': np.iinfo,
                 'u': np.iinfo}
        rng = infos[kind](dtype)
        return rng.min <= value <= rng.max

    with ctx.obj['env'], rasterio.open(input, 'r+') as dst:

        if allmd:
            nodata = allmd['nodata']
            crs = allmd['crs']
            transform = allmd['transform']
            tags = allmd['tags']

        if unset_nodata and nodata is not options.IgnoreOption:
            raise click.BadParameter(
                "--unset-nodata and --nodata cannot be used together.")

        if unset_crs and crs:
            raise click.BadParameter(
                "--unset-crs and --crs cannot be used together.")

        if unset_nodata:
            # Setting nodata to None will raise NotImplementedError
            # if GDALDeleteRasterNoDataValue() isn't present in the
            # GDAL library.
            try:
                dst.nodata = None
            except NotImplementedError as exc:  # pragma: no cover
                raise click.ClickException(str(exc))

        elif nodata is not options.IgnoreOption:
            dtype = dst.dtypes[0]
            if nodata is not None and not in_dtype_range(nodata, dtype):
                raise click.BadParameter(
                    "outside the range of the file's "
                    "data type (%s)." % dtype,
                    param=nodata, param_hint='nodata')
            dst.nodata = nodata

        if unset_crs:
            dst.crs = None  # CRS()
        elif crs:
            dst.crs = crs

        if transform:
            dst.transform = transform

        if tags:
            dst.update_tags(**tags)

        if units:
            dst.set_units(bidx, units)

        if description:
            dst.set_description(bidx, description)

    # Post check - ensure that crs was unset properly
    if unset_crs:
        with ctx.obj['env'], rasterio.open(input, 'r') as src:
            if src.crs:
                warnings.warn(
                    'CRS was not unset. Availability of his functionality '
                    'differs depending on GDAL version and driver')
