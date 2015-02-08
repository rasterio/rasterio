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
@files_inout_arg
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
    *

    
    Calculations on all bands of a
    dataset can be specified using 
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

                # Using the class method instead of instance method.
                # Latter raises
                # TypeError: astype() got an unexpected keyword argument 'copy'
                # Possibly something to do with the instance being a masked
                # array.
                sources = np.ma.asanyarray([np.ndarray.astype(
                                rasterio.open(path).read(),
                                'float64',
                                copy=False
                            ) for path in files])

                # TODO: implement a real parser for calc expressions,
                # perhaps using numexpr's parser as a guide, instead
                # eval'ing any string.

                parts = command.split(';')
                if len(parts) == 1:

                    # Translates, eg, '{1}' to 'sources[0]'.
                    cmd = re.sub(
                            r'{(\d)}',
                            lambda m: 'sources[%d]' % (int(m.group(1))-1),
                            parts.pop())

                    logger.debug("Translated cmd: %r", cmd)

                    results = eval(cmd)
                    results = np.ndarray.astype(results, dtype, copy=False)

                    # Write results.
                    if len(results.shape) == 3:
                        kwargs['count'] = results.shape[0]
                        with rasterio.open(output, 'w', **kwargs) as dst:
                            dst.write(results)

                    elif len(results.shape) == 2:
                        kwargs['count'] = 1
                        with rasterio.open(output, 'w', **kwargs) as dst:
                            dst.write(results, 1)

                else:
                    parts = list(filter(lambda p: p.strip(), parts))
                    kwargs['count'] = len(parts)

                    results = []

                    for part in parts:
                        cmd = re.sub(
                                r'{(\d)\s*,\s*(\d)}',
                                lambda m: 'sources[%d,%d]' % (
                                    int(m.group(1))-1, int(m.group(2))-1),
                                part)

                        logger.debug("Translated cmd: %r", cmd)

                        res = eval(cmd)
                        res = np.ndarray.astype(res, dtype, copy=False)
                        results.append(res)

                    results = np.asanyarray(results)
                    kwargs['count'] = results.shape[0]
                    with rasterio.open(output, 'w', **kwargs) as dst:
                        dst.write(results)

        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)
