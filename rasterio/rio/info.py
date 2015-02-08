# Info command.

import json
import logging
import os.path
import pprint
import sys

import click

import rasterio
import rasterio.crs
from rasterio.rio.cli import cli


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
@click.argument('input', type=click.Path(exists=True))
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
@click.option('--dtype', 'meta_member', flag_value='dtype',
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
@click.option('--res', 'meta_member', flag_value='res',
              help="Print pixel width and height.")
@click.option('--lnglat', 'meta_member', flag_value='lnglat',
              help="Print longitude and latitude at center.")
@click.option('--stats', 'meta_member', flag_value='stats',
              help="Print statistics (min, max, mean) of a single band "
                   "(use --bidx).")
@click.option('-v', '--tell-me-more', '--verbose', is_flag=True,
              help="Output extra information.")
@click.option('--bidx', type=int, default=1,
              help="Input file band index (default: 1).")
@click.pass_context
def info(ctx, input, aspect, indent, namespace, meta_member, verbose, bidx):
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
                del info['affine']
                del info['transform']
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
                              'mean': float(b.mean())} for b in src.read()]
                    info['stats'] = stats
                if aspect == 'meta':
                    if meta_member == 'stats':
                        band = src.read(bidx)
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
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
