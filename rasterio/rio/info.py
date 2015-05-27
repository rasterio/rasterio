"""Fetch and edit raster dataset metadata from the command line."""

import json
import logging
import sys

import click

import rasterio
import rasterio.crs
from rasterio.rio.cli import cli, bidx_opt, file_in_arg, masked_opt
from rasterio.transform import guard_transform


@cli.command('edit-info', short_help="Edit dataset metadata.")
@file_in_arg
@click.option('--nodata', type=float, default=None,
              help="New nodata value")
@click.option('--crs', help="New coordinate reference system")
@click.option('--transform', help="New affine transform matrix")
@click.option('--tag', 'tags', multiple=True, metavar='KEY=VAL',
              help="New tag.")
@click.pass_context
def edit(ctx, input, nodata, crs, transform, tags):
    """Edit a dataset's metadata: coordinate reference system, affine
    transformation matrix, nodata value, and tags.

    CRS may be either a PROJ.4 or EPSG:nnnn string, or a JSON-encoded
    PROJ.4 object.

    Transforms are either JSON-encoded Affine objects (preferred) like

      [300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]

    or JSON-encoded GDAL geotransform arrays like

      [101985.0, 300.038, 0.0, 2826915.0, 0.0, -300.042]
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

            # Update nodata.
            if nodata is not None:

                dtype = dst.dtypes[0]
                if not in_dtype_range(nodata, dtype):
                    raise click.BadParameter(
                        "outside the range of the file's "
                        "data type (%s)." % dtype,
                        param=nodata, param_hint='nodata')

                dst.nodata = nodata

            # Update CRS. Value might be a PROJ.4 string or a JSON
            # encoded dict.
            if crs:
                new_crs = crs.strip()
                try:
                    new_crs = json.loads(crs)
                except ValueError:
                    pass

                if not (rasterio.crs.is_geographic_crs(new_crs) or 
                        rasterio.crs.is_projected_crs(new_crs)):
                    raise click.BadParameter(
                        "'%s' is not a recognized CRS." % crs,
                        param=crs, param_hint='crs')

                dst.crs = new_crs

            # Update transform. Value might be a JSON encoded
            # Affine object or a GDAL geotransform array.
            if transform:
                try:
                    transform_obj = json.loads(transform)
                except ValueError:
                    raise click.BadParameter(
                        "'%s' is not a JSON array." % transform,
                        param=transform, param_hint='transform')

                try:
                    transform_obj = guard_transform(transform_obj)
                except:
                    raise click.BadParameter(
                        "'%s' is not recognized as an Affine or GDAL "
                        "geotransform array." % transform,
                        param=transform, param_hint='transform')

                dst.transform = transform_obj

            # Update tags.
            if tags:
                tags = dict(p.split('=') for p in tags)
                dst.update_tags(**tags)


@cli.command(short_help="Print information about the rio environment.")
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


@cli.command(short_help="Print information about a data file.")
@file_in_arg
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
@click.option('-v', '--tell-me-more', '--verbose', is_flag=True,
              help="Output extra information.")
@bidx_opt
@masked_opt
@click.pass_context
def info(ctx, input, aspect, indent, namespace, meta_member, verbose, bidx,
        masked):
    """Print metadata about the dataset as JSON.

    Optionally print a single metadata item as a string.
    """
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')
    mode = 'r' if (verbose or meta_member == 'stats') else 'r-'

    try:
        with rasterio.drivers(CPL_DEBUG=(verbosity > 2)):
            with rasterio.open(input, mode) as src:
                info = src.meta
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
                if aspect == 'meta':
                    if meta_member == 'stats':
                        band = src.read(bidx, masked=masked)
                        click.echo('%f %f %f' % (
                            float(band.min()),
                            float(band.max()),
                            float(band.mean())))
                    elif meta_member:
                        if isinstance(info[meta_member], (list, tuple)):
                            click.echo(" ".join(map(str, info[meta_member])))
                        else:
                            click.echo(info[meta_member])
                    else:
                        click.echo(json.dumps(info, indent=indent))
                elif aspect == 'tags':
                    click.echo(json.dumps(src.tags(ns=namespace),
                                            indent=indent))
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()
