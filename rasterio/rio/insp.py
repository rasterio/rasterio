"""Fetch and edit raster dataset metadata from the command line."""

import logging
import sys

import click

from . import options
import rasterio


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
    logger = logging.getLogger('rio')
    try:
        with rasterio.drivers(CPL_DEBUG=verbosity > 2):
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
