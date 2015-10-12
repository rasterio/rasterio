# Calc command.

from distutils.version import LooseVersion
import logging

import click
import snuggs
from cligj import files_inout_arg

from .helpers import resolve_inout
from . import options
import rasterio
from rasterio.fill import fillnodata
from rasterio.features import sieve


def get_bands(inputs, d, i=None):
    """Get a rasterio.Band object from calc's inputs"""
    path = inputs[d] if d in dict(inputs) else inputs[int(d)-1][1]
    src = rasterio.open(path)
    return (rasterio.band(src, i) if i else 
            [rasterio.band(src, i) for i in src.indexes])


def read_array(ix, subix=None, dtype=None):
    """Change the type of a read array"""
    arr = snuggs._ctx.lookup(ix, subix)
    if dtype:
        arr = arr.astype(dtype)
    return arr


@click.command(short_help="Raster data calculator.")
@click.argument('command')
@files_inout_arg
@options.output_opt
@click.option('--name', multiple=True,
              help='Specify an input file with a unique short (alphas only) '
                   'name for use in commands like '
                   '"a=tests/data/RGB.byte.tif".')
@options.dtype_opt
@options.masked_opt
@options.creation_options
@click.pass_context
def calc(ctx, command, files, output, name, dtype, masked, creation_options):
    """A raster data calculator

    Evaluates an expression using input datasets and writes the result
    to a new dataset.

    Command syntax is lisp-like. An expression consists of an operator
    or function name and one or more strings, numbers, or expressions
    enclosed in parentheses. Functions include ``read`` (gets a raster
    array) and ``asarray`` (makes a 3-D array from 2-D arrays).

    \b
        * (read i) evaluates to the i-th input dataset (a 3-D array).
        * (read i j) evaluates to the j-th band of the i-th dataset (a 2-D
          array).
        * (take foo j) evaluates to the j-th band of a dataset named foo (see
          help on the --name option above).
        * Standard numpy array operators (+, -, *, /) are available.
        * When the final result is a list of arrays, a multi band output
          file is written.
        * When the final result is a single array, a single band output
          file is written.

    Example:

    \b
         $ rio calc "(+ 2 (* 0.95 (read 1)))" tests/data/RGB.byte.tif \\
         > /tmp/out.tif

    Produces a 3-band GeoTIFF with all values scaled by 0.95 and
    incremented by 2.

    \b
        $ rio calc "(asarray (+ 125 (read 1)) (read 1) (read 1))" \\
        > tests/data/shade.tif /tmp/out.tif

    Produces a 3-band RGB GeoTIFF, with red levels incremented by 125,
    from the single-band input.

    """
    import numpy as np

    verbosity = (ctx.obj and ctx.obj.get('verbosity')) or 1
    logger = logging.getLogger('rio')

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity > 2):
            output, files = resolve_inout(files=files, output=output)

            inputs = ([tuple(n.split('=')) for n in name] +
                      [(None, n) for n in files])

            with rasterio.open(inputs[0][1]) as first:
                kwargs = first.meta
                kwargs.update(**creation_options)
                kwargs['transform'] = kwargs.pop('affine')
                dtype = dtype or first.meta['dtype']
                kwargs['dtype'] = dtype

            ctxkwds = {}
            for i, (name, path) in enumerate(inputs):
                with rasterio.open(path) as src:
                    # Using the class method instead of instance
                    # method. Latter raises
                    #
                    # TypeError: astype() got an unexpected keyword
                    # argument 'copy'
                    #
                    # possibly something to do with the instance being
                    # a masked array.
                    ctxkwds[name or '_i%d' % (i+1)] = src.read(masked=masked)

            # Extend snuggs.
            snuggs.func_map['read'] = read_array
            snuggs.func_map['band'] = lambda d, i: get_bands(inputs, d, i)
            snuggs.func_map['bands'] = lambda d: get_bands(inputs, d)
            snuggs.func_map['fillnodata'] = lambda *args: fillnodata(*args)
            snuggs.func_map['sieve'] = lambda *args: sieve(*args)

            res = snuggs.eval(command, **ctxkwds)

            if isinstance(res, np.ma.core.MaskedArray):
                res = res.filled(kwargs['nodata'])

            if len(res.shape) == 3:
                results = np.ndarray.astype(res, dtype, copy=False)
            else:
                results = np.asanyarray(
                    [np.ndarray.astype(res, dtype, copy=False)])

            kwargs['count'] = results.shape[0]

            with rasterio.open(output, 'w', **kwargs) as dst:
                dst.write(results)

    except snuggs.ExpressionError as err:
        click.echo("Expression Error:")
        click.echo('  %s' % err.text)
        click.echo(' ' +  ' ' * err.offset + "^")
        click.echo(err)
        raise click.Abort()
