
import code
import collections
import logging

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

import numpy

import rasterio
from rasterio.five import zip_longest


logger = logging.getLogger('rasterio')

Stats = collections.namedtuple('Stats', ['min', 'max', 'mean'])

# Collect dictionary of functions for use in the interpreter in main()
funcs = locals()


def show(source, cmap='gray', with_bounds=True):
    """
    Display a raster or raster band using matplotlib.

    Parameters
    ----------
    source : array-like or (raster dataset, bidx)
        If array-like, should be of format compatible with
        matplotlib.pyplot.imshow. If the tuple (raster dataset, bidx),
        selects band `bidx` from raster.
    cmap : str (opt)
        Specifies the colormap to use in plotting. See
        matplotlib.Colors.Colormap. Default is 'gray'.
    with_bounds : bool (opt)
        Whether to change the image extent to the spatial bounds of the image,
        rather than pixel coordinates. Only works when source is
        (raster dataset, bidx).
    """

    if isinstance(source, tuple):
        arr = source[0].read(source[1])
        xs = source[0].res[0] / 2.
        ys = source[0].res[1] / 2.
        if with_bounds:
            extent = (source[0].bounds.left - xs, source[0].bounds.right - xs,
                      source[0].bounds.bottom - ys, source[0].bounds.top - ys)
        else:
            extent = None
    else:
        arr = source
        extent = None
    if plt is not None:
        imax = plt.imshow(arr, cmap=cmap, extent=extent)
        fig = plt.gcf()
        fig.show()
    else:
        raise ImportError("matplotlib could not be imported")


def stats(source):
    """Return a tuple with raster min, max, and mean.
    """
    if isinstance(source, tuple):
        arr = source[0].read(source[1])
    else:
        arr = source
    return Stats(numpy.min(arr), numpy.max(arr), numpy.mean(arr))


def show_hist(source, bins=10, masked=True, title='Histogram'):

    """
    Easily display a histogram with matplotlib.

    Parameters
    ----------
    bins : int, optional
        Compute histogram across N bins.
    data : np.array or rasterio.Band or tuple(dataset, bidx)
        Input data to display.  The first three arrays in multi-dimensional
        arrays are plotted as red, green, and blue.
    masked : bool, optional
        When working with a `rasterio.Band()` object, specifies if the data
        should be masked on read.
    title : str, optional
        Title for the figure.
    """

    if plt is None:
        raise ImportError("Could not import matplotlib")

    if isinstance(source, (tuple, rasterio.Band)):
        arr = source[0].read(source[1], masked=masked)
    else:
        arr = source

    # The histogram is computed individually for each 'band' in the array
    # so we need the overall min/max to constrain the plot
    rng = arr.min(), arr.max()

    if len(arr.shape) is 2:
        arr = [arr]
        colors = ['gold']
    else:
        colors = ('red', 'green', 'blue', 'violet', 'gold', 'saddlebrown')

    # If a rasterio.Band() is given make sure the proper index is displayed
    # in the legend.
    if isinstance(source, (tuple, rasterio.Band)):
        labels = [str(source[1])]
    else:
        labels = (str(i + 1) for i in range(len(arr)))

    # This loop should add a single plot each band in the input array,
    # regardless of if the number of bands exceeds the number of colors.
    # The colors slicing ensures that the number of iterations always
    # matches the number of bands.
    # The goal is to provide a curated set of colors for working with
    # smaller datasets and let matplotlib define additional colors when
    # working with larger datasets.
    for bnd, color, label in zip_longest(arr, colors[:len(arr)], labels):

        plt.hist(
            bnd.flatten(),
            bins=bins,
            alpha=0.5,
            color=color,
            label=label,
            range=rng
        )

    plt.legend(loc="upper right")
    plt.title(title, fontweight='bold')
    plt.grid(True)
    plt.xlabel('DN')
    plt.ylabel('Frequency')
    fig = plt.gcf()
    fig.show()


def main(banner, dataset, alt_interpreter=None):
    """ Main entry point for use with python interpreter """
    local = dict(funcs, src=dataset, np=numpy, rio=rasterio, plt=plt)
    if not alt_interpreter:
        code.interact(banner, local=local)
    elif alt_interpreter == 'ipython':
        import IPython
        IPython.InteractiveShell.banner1 = banner
        IPython.start_ipython(argv=[], user_ns=local)
    else:
        raise ValueError("Unsupported interpreter '%s'" % alt_interpreter)

    return 0
