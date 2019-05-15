"""$ rio calc"""

from __future__ import division

from collections import OrderedDict
from distutils.version import LooseVersion
import math

import click
import snuggs

import rasterio
from rasterio.features import sieve
from rasterio.fill import fillnodata
from rasterio.windows import Window
from rasterio.rio import options
from rasterio.rio.helpers import resolve_inout


def _get_bands(inputs, sources, d, i=None):
    """Get a rasterio.Band object from calc's inputs"""
    idx = d if d in dict(inputs) else int(d) - 1
    src = sources[idx]
    return (rasterio.band(src, i) if i else
            [rasterio.band(src, j) for j in src.indexes])


def _read_array(ix, subix=None, dtype=None):
    """Change the type of a read array"""
    arr = snuggs._ctx.lookup(ix, subix)
    if dtype:
        arr = arr.astype(dtype)
    return arr


def _chunk_output(width, height, count, itemsize, mem_limit=1):
    """Divide the calculation output into chunks

    This function determines the chunk size such that an array of shape
    (chunk_size, chunk_size, count) with itemsize bytes per element
    requires no more than mem_limit megabytes of memory.

    Output chunks are described by rasterio Windows.

    Parameters
    ----------
    width : int
        Output width
    height : int
        Output height
    count : int
        Number of output bands
    itemsize : int
        Number of bytes per pixel
    mem_limit : int, default
        The maximum size in memory of a chunk array

    Returns
    -------
    sequence of Windows
    """
    max_pixels = mem_limit * 1.0e+6 / itemsize * count
    chunk_size = int(math.floor(math.sqrt(max_pixels)))
    ncols = int(math.ceil(width / chunk_size))
    nrows = int(math.ceil(height / chunk_size))
    chunk_windows = []

    for col in range(ncols):
        col_offset = col * chunk_size
        w = min(chunk_size, width - col_offset)
        for row in range(nrows):
            row_offset = row * chunk_size
            h = min(chunk_size, height - row_offset)
            chunk_windows.append(((row, col), Window(col_offset, row_offset, w, h)))

    return chunk_windows


@click.command(short_help="Raster data calculator.")
@click.argument('command')
@options.files_inout_arg
@options.output_opt
@click.option('--name', multiple=True,
              help='Specify an input file with a unique short (alphas only) '
                   'name for use in commands like '
                   '"a=tests/data/RGB.byte.tif".')
@options.dtype_opt
@options.masked_opt
@options.overwrite_opt
@click.option("--mem-limit", type=int, default=64, help="Limit on size of scratch space, in MB.")
@options.creation_options
@click.pass_context
def calc(ctx, command, files, output, name, dtype, masked, overwrite, mem_limit, creation_options):
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

    try:
        with ctx.obj['env']:
            output, files = resolve_inout(files=files, output=output,
                                          overwrite=overwrite)
            inputs = ([tuple(n.split('=')) for n in name] +
                      [(None, n) for n in files])
            sources = [rasterio.open(path) for name, path in inputs]

            first = sources[0]
            kwargs = first.profile
            kwargs.update(**creation_options)
            dtype = dtype or first.meta['dtype']
            kwargs['dtype'] = dtype

            # Extend snuggs.
            snuggs.func_map['read'] = _read_array
            snuggs.func_map['band'] = lambda d, i: _get_bands(inputs, sources, d, i)
            snuggs.func_map['bands'] = lambda d: _get_bands(inputs, sources, d)
            snuggs.func_map['fillnodata'] = lambda *args: fillnodata(*args)
            snuggs.func_map['sieve'] = lambda *args: sieve(*args)

            dst = None

            # The windows iterator is initialized with a single sample.
            # The actual work windows will be added in the second
            # iteration of the loop.
            work_windows = [(None, Window(0, 0, 16, 16))]

            for ij, window in work_windows:

                ctxkwds = OrderedDict()

                for i, ((name, path), src) in enumerate(zip(inputs, sources)):

                    # Using the class method instead of instance
                    # method. Latter raises
                    #
                    # TypeError: astype() got an unexpected keyword
                    # argument 'copy'
                    #
                    # possibly something to do with the instance being
                    # a masked array.
                    ctxkwds[name or '_i%d' % (i + 1)] = src.read(masked=masked, window=window)

                res = snuggs.eval(command, **ctxkwds)

                if (isinstance(res, np.ma.core.MaskedArray) and (
                        tuple(LooseVersion(np.__version__).version) < (1, 9) or
                        tuple(LooseVersion(np.__version__).version) > (1, 10))):
                    res = res.filled(kwargs['nodata'])

                if len(res.shape) == 3:
                    results = np.ndarray.astype(res, dtype, copy=False)
                else:
                    results = np.asanyarray(
                        [np.ndarray.astype(res, dtype, copy=False)])

                # The first iteration is only to get sample results and from them
                # compute some properties of the output dataset.
                if dst is None:
                    kwargs['count'] = results.shape[0]
                    dst = rasterio.open(output, 'w', **kwargs)
                    work_windows.extend(_chunk_output(dst.width, dst.height, dst.count, np.dtype(dst.dtypes[0]).itemsize, mem_limit=mem_limit))

                # In subsequent iterations we write results.
                else:
                    dst.write(results, window=window)

    except snuggs.ExpressionError as err:
        click.echo("Expression Error:")
        click.echo('  %s' % err.text)
        click.echo(' ' + ' ' * err.offset + "^")
        click.echo(err)
        raise click.Abort()

    finally:
        if dst:
            dst.close()
        for src in sources:
            src.close()
