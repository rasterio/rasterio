"""Command access to dataset metadata, stats, and more."""


import json

import click

import rasterio
import rasterio.crs
from rasterio.rio import options


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
    try:
        with ctx.obj['env'], rasterio.open(input) as src:

            info = dict(src.profile)
            info['shape'] = (info['height'], info['width'])
            info['bounds'] = src.bounds
            proj4 = src.crs.to_string()
            if proj4.startswith('+init=epsg'):
                proj4 = proj4.split('=')[1].upper()
            info['crs'] = proj4
            info['res'] = src.res
            info['colorinterp'] = [src.colorinterp(i).name
                                   for i in src.indexes]
            info['units'] = src.units
            info['description'] = src.description
            info['band_descriptions'] = src.band_descriptions
            info['indexes'] = src.indexes

            if proj4 != '':
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
        raise click.Abort()
