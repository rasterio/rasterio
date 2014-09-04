
import code
import collections
import logging
import sys

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

import numpy

import rasterio


logger = logging.getLogger('rasterio')

Stats = collections.namedtuple('Stats', ['min', 'max', 'mean'])

def main(banner, dataset):

    def show(source, cmap='gray'):
        """Show a raster using matplotlib.

        The raster may be either an ndarray or a (dataset, bidx)
        tuple.
        """
        if isinstance(source, tuple):
            arr = source[0].read_band(source[1])
        else:
            arr = source
        if plt is not None:
            plt.imshow(arr, cmap=cmap)
            plt.show()
        else:
            raise ImportError("matplotlib could not be imported")

    def stats(source):
        """Return a tuple with raster min, max, and mean.
        """
        if isinstance(source, tuple):
            arr = source[0].read_band(source[1])
        else:
            arr = source
        return Stats(numpy.min(arr), numpy.max(arr), numpy.mean(arr))

    code.interact(
        banner, 
        local=dict(
            locals(), src=dataset, np=numpy, rio=rasterio, plt=plt))

    return 0
