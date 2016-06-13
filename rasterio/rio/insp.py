"""Fetch and edit raster dataset metadata from the command line."""
from __future__ import absolute_import

import code
import logging
import sys
import collections
import warnings

import numpy as np
import click

from . import options
import rasterio
from rasterio.plot import show, show_hist

try:
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None
except RuntimeError as e:  # pragma: no cover
    # Certain environment configurations can trigger a RuntimeError like:

    # Trying to import matplotlibRuntimeError: Python is not installed as a
    # framework. The Mac OS X backend will not be able to function correctly
    # if Python is not installed as a framework. See the Python ...
    warnings.warn(str(e), RuntimeWarning, stacklevel=2)
    plt = None


logger = logging.getLogger('rasterio')

Stats = collections.namedtuple('Stats', ['min', 'max', 'mean'])

# Collect dictionary of functions for use in the interpreter in main()
funcs = locals()


def stats(source):
    """Return a tuple with raster min, max, and mean."""
    if isinstance(source, tuple):
        arr = source[0].read(source[1])
    else:
        arr = source
    return Stats(np.min(arr), np.max(arr), np.mean(arr))


def main(banner, dataset, alt_interpreter=None):
    """Main entry point for use with python interpreter."""
    local = dict(funcs, src=dataset, np=np, rio=rasterio, plt=plt)
    if not alt_interpreter:
        code.interact(banner, local=local)
    elif alt_interpreter == 'ipython':  # pragma: no cover
        import IPython
        IPython.InteractiveShell.banner1 = banner
        IPython.start_ipython(argv=[], user_ns=local)
    else:
        raise ValueError("Unsupported interpreter '%s'" % alt_interpreter)

    return 0


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
    """Open the input file in a Python interpreter."""
    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')
    try:
        with rasterio.Env(CPL_DEBUG=verbosity > 2):
            with rasterio.open(input, mode) as src:
                main(
                    'Rasterio %s Interactive Inspector (Python %s)\n'
                    'Type "src.meta", "src.read(1)", or "help(src)" '
                    'for more information.' % (
                        rasterio.__version__,
                        '.'.join(map(str, sys.version_info[:3]))),
                    src, interpreter)
    except Exception:
        logger.exception("Exception caught during processing")
        raise click.Abort()
