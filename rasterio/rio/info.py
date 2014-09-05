# Info command.

import json
import logging
import os.path
import pprint
import sys

import click
import rasterio

from rasterio.rio.cli import cli

@cli.command(short_help="Print information about a data file.")

@click.argument('src_path', type=click.Path(exists=True))

@click.option('--meta', 'aspect', flag_value='meta', default=True,
              help="Show data file structure (default).")

@click.option('--tags', 'aspect', flag_value='tags',
              help="Show data file tags.")

@click.option('--indent', default=2, type=int,
              help="Indentation level for pretty printed output")

@click.option('--namespace', help="Select a tag namespace.")

@click.option('--count', 'meta_member', flag_value='count',
              help="Print the count of bands.")

@click.option('--dtype', 'meta_member', flag_value='dtype',
              help="Print the dtype name.")

@click.option('--nodata', 'meta_member', flag_value='nodata',
              help="Print the nodata value.")

@click.option('--shape', 'meta_member', flag_value='shape',
              help="Print the nodata value.")

@click.pass_context

def info(ctx, src_path, aspect, indent, namespace, meta_member):
    verbosity = ctx.obj['verbosity']
    logger = logging.getLogger('rio')
    stdout = click.get_text_stream('stdout')
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            with rasterio.open(src_path, 'r-') as src:
                info = src.meta
                info['shape'] = info['height'], info['width']
                if aspect == 'meta':
                    if meta_member:
                        if isinstance(info[meta_member], (list, tuple)):
                            print(" ".join(map(str, info[meta_member])))
                        else:
                            print(info[meta_member])
                    else:
                        stdout.write(json.dumps(info, indent=indent))
                        stdout.write("\n")
                elif aspect == 'tags':
                    stdout.write(json.dumps(src.tags(ns=namespace), 
                                            indent=indent))
                    stdout.write("\n")
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
