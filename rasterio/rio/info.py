"""Fetch and edit raster dataset metadata from the command line."""


import json
import logging
import os
import sys

import click
from cligj import precision_opt

from . import options
import rasterio
from rasterio import aws
import rasterio.crs
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
    logger = logging.getLogger('rio')

    def in_dtype_range(value, dtype):
        infos = {'c': np.finfo, 'f': np.finfo, 'i': np.iinfo,
                 'u': np.iinfo}
        rng = infos[np.dtype(dtype).kind](dtype)
        return rng.min <= value <= rng.max

    with rasterio.drivers(CPL_DEBUG=(verbosity > 2)) as env:

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


@click.command(short_help="Print information about the rio environment.")
@click.option('--formats', 'key', flag_value='formats', default=True,
              help="Enumerate the available formats.")
@click.pass_context
def env(ctx, key):
    """Print information about the Rasterio environment: available
    formats, etc.
    """
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')
    stdout = click.get_text_stream('stdout')
    with rasterio.drivers(CPL_DEBUG=(verbosity > 2)) as env:
        if key == 'formats':
            for k, v in sorted(env.drivers().items()):
                stdout.write("%s: %s\n" % (k, v))
            stdout.write('\n')


@click.command(short_help="Print information about a data file.")
@options.file_in_arg
@click.option('--meta', 'aspect', flag_value='meta', default=True,
              help="Show data file structure (default).")
@click.option('--tags', 'aspect', flag_value='tags',
              help="Show data file tags.")
@click.option('--namespace', help="Select a tag namespace.")
@click.option('--indent', default=None, type=int,
              help="Indentation level for pretty printed output")
# Options to pick out a single metadata item and print it as
# a string.
@click.option('--count', 'meta_member', flag_value='count',
              help="Print the count of bands.")
@click.option('-t', '--dtype', 'meta_member', flag_value='dtype',
              help="Print the dtype name.")
@click.option('--nodata', 'meta_member', flag_value='nodata',
              help="Print the nodata value.")
@click.option('-f', '--format', '--driver', 'meta_member', flag_value='driver',
              help="Print the format driver.")
@click.option('--shape', 'meta_member', flag_value='shape',
              help="Print the (height, width) shape.")
@click.option('--height', 'meta_member', flag_value='height',
              help="Print the height (number of rows).")
@click.option('--width', 'meta_member', flag_value='width',
              help="Print the width (number of columns).")
@click.option('--crs', 'meta_member', flag_value='crs',
              help="Print the CRS as a PROJ.4 string.")
@click.option('--bounds', 'meta_member', flag_value='bounds',
              help="Print the boundary coordinates "
                   "(left, bottom, right, top).")
@click.option('-r', '--res', 'meta_member', flag_value='res',
              help="Print pixel width and height.")
@click.option('--lnglat', 'meta_member', flag_value='lnglat',
              help="Print longitude and latitude at center.")
@click.option('--stats', 'meta_member', flag_value='stats',
              help="Print statistics (min, max, mean) of a single band "
                   "(use --bidx).")
@click.option('--checksum', 'meta_member', flag_value='checksum',
              help="Print integer checksum of a single band "
                   "(use --bidx).")
@click.option('-v', '--tell-me-more', '--verbose', is_flag=True,
              help="Output extra information.")
@options.bidx_opt
@options.masked_opt
@click.pass_context
def info(ctx, input, aspect, indent, namespace, meta_member, verbose, bidx,
         masked):
    """Print metadata about the dataset as JSON.

    Optionally print a single metadata item as a string.
    """
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    aws_session = ctx.obj.get('aws_session')

    logger = logging.getLogger('rio')
    mode = 'r' if (verbose or meta_member == 'stats') else 'r-'
    try:
        with rasterio.drivers(
                CPL_DEBUG=(verbosity > 2)), aws_session:
            with rasterio.open(input, mode) as src:
                info = src.profile
                info['transform'] = info['affine'][:6]
                del info['affine']
                info['shape'] = info['height'], info['width']
                info['bounds'] = src.bounds
                proj4 = rasterio.crs.to_string(src.crs)
                if proj4.startswith('+init=epsg'):
                    proj4 = proj4.split('=')[1].upper()
                info['crs'] = proj4
                info['res'] = src.res
                info['lnglat'] = src.lnglat()
                if verbose:
                    stats = [{'min': float(b.min()),
                              'max': float(b.max()),
                              'mean': float(b.mean())
                              } for b in src.read(masked=masked)]
                    info['stats'] = stats
                    info['checksum'] = [src.checksum(i) for i in src.indexes]
                if aspect == 'meta':
                    if meta_member == 'stats':
                        band = src.read(bidx, masked=masked)
                        click.echo('%f %f %f' % (
                            float(band.min()),
                            float(band.max()),
                            float(band.mean())))
                    elif meta_member == 'checksum':
                        click.echo(str(src.checksum(bidx)))
                    elif meta_member:
                        if isinstance(info[meta_member], (list, tuple)):
                            click.echo(" ".join(map(str, info[meta_member])))
                        else:
                            click.echo(info[meta_member])
                    else:
                        click.echo(json.dumps(info, indent=indent))
                elif aspect == 'tags':
                    click.echo(
                        json.dumps(src.tags(ns=namespace), indent=indent))
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()


# Insp command.
@click.command(short_help="Open a data file and start an interpreter.")
@options.file_in_arg
@click.option('--ipython', 'interpreter', flag_value='ipython',
              help="Use IPython as interpreter.")
@click.option(
    '-m',
    '--mode',
    type=click.Choice(['r', 'r+']),
    default='r',
    help="File mode (default 'r').")
@click.pass_context
def insp(ctx, input, mode, interpreter):
    """ Open the input file in a Python interpreter.
    """
    import rasterio.tool
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    aws_session = (ctx.obj and ctx.obj.get('aws_session'))
    logger = logging.getLogger('rio')
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity > 2), aws_session:
            with rasterio.open(input, mode) as src:
                rasterio.tool.main(
                    'Rasterio %s Interactive Inspector (Python %s)\n'
                    'Type "src.meta", "src.read(1)", or "help(src)" '
                    'for more information.' % (
                        rasterio.__version__,
                        '.'.join(map(str, sys.version_info[:3]))),
                    src, interpreter)
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()


# Transform command.
@click.command(short_help="Transform coordinates.")
@click.argument('INPUT', default='-', required=False)
@click.option('--src-crs', '--src_crs', default='EPSG:4326',
              help="Source CRS.")
@click.option('--dst-crs', '--dst_crs', default='EPSG:4326',
              help="Destination CRS.")
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
        with rasterio.drivers(CPL_DEBUG=verbosity > 2):
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
