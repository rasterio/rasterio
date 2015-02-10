# Calc command.

import logging
import math
import os.path
import re
import sys
import warnings

import click
from cligj import files_inout_arg

import rasterio
from rasterio.rio.cli import cli


@cli.command(short_help="Raster data calculator.")
@click.argument('command')
@click.argument(
    'files',
    nargs=-1,
    type=click.Path(resolve_path=False),
    required=True,
    metavar="INPUTS... OUTPUT")
@click.option('--dtype', 
              type=click.Choice([
                'ubyte', 'uint8', 'uint16', 'int16', 'uint32',
                'int32', 'float32', 'float64']),
                default='float64',
              help="Output data type (default: float64).")
@click.pass_context
def calc(ctx, command, files, dtype):
    """A raster data calculator

    Applies one or more commands to a set of input datasets and writes
    the results to a new dataset.

    Command syntax is a work in progress. Currently:
    
    * {n} represents the n-th input dataset (a 3-D array)
    * {n,m} represents the m-th band of the n-th dataset (a 2-D array).
    * Standard numpy array operators (+, -, *, /) are available.
    * Multiple commands delimited by ; may be executed.
    * The result of the previous command is represented by {}.
    * When the final result is a tuple of arrays, a multi band output
      file is written.
    * When the final result is a single array, a single band output
      file is written.

    """
    import numpy as np

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            output = files[-1]
            files = files[:-1]

            with rasterio.open(files[0]) as first:
                kwargs = first.meta
                kwargs['transform'] = kwargs.pop('affine')
                kwargs['dtype'] = dtype

            names = []
            sources = []
            for path in files:
                with rasterio.open(path) as src:
                    names.append(src.name)
                    # Using the class method instead of instance method.
                    # Latter raises
                    # TypeError: astype() got an unexpected keyword argument 'copy'
                    # Possibly something to do with the instance being a masked
                    # array.
                    sources.append(
                        np.ndarray.astype(src.read(), 'float64', copy=False))

            #sources = np.ma.asanyarray([s for s in sources])

            parts = command.split(';')
            _prev = None

            def cmd_sources(match):
                text = match.group(1)
                parts = text.split(',')
                v = parts.pop(0)
                if v in names:
                    a = names.index(v)
                s = 'sources[%d]' % a
                if parts:
                    s += '[%d]' % (int(parts.pop(0)) - 1)
                return s

            for part in filter(lambda p: p.strip(), parts):

                # TODO: implement a real parser for calc expressions,
                # perhaps using numexpr's parser as a guide, instead
                # eval'ing any string.

                # Translate '{}' to '_prev'.
                cmd = re.sub(r'{}', '_prev', part)

                cmd = re.sub(
                        r'{(\d+),(\d+)}',
                        lambda m: 'sources[%d][%d]' % (
                            int(m.group(1))-1,
                            int(m.group(2))-1),
                        cmd)

                cmd = re.sub(
                        r'{(\d+)}',
                        lambda m: 'sources[%d]' % (int(m.group(1))-1),
                        cmd)

                cmd = re.sub(r'{(.+)}', cmd_sources, cmd)

                logger.debug("Translated cmd: %r", cmd)

                res = eval(cmd)
                _prev = res

            if isinstance(res, tuple) or len(res.shape) == 3:
                results = np.asanyarray([
                            np.ndarray.astype(r, dtype, copy=False
                            ) for r in res])
            else:
                results = np.asanyarray(
                    [np.ndarray.astype(res, dtype, copy=False)])

            kwargs['count'] = results.shape[0]
            with rasterio.open(output, 'w', **kwargs) as dst:
                dst.write(results)

        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
