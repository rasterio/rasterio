
import code
import collections
import logging
import sys

import numpy

import rasterio


logger = logging.getLogger('rasterio')

Stats = collections.namedtuple('Stats', ['min', 'max', 'mean'])

def main(banner, dataset):

    def show(source):
        """Show a raster using matplotlib.

        The raster may be either an ndarray or a (dataset, bidx)
        tuple.
        """
        import matplotlib.pyplot as plt
        if isinstance(source, tuple):
            arr = source[0].read_band(source[1])
        else:
            arr = source
        plt.imshow(arr)
        plt.gray()
        plt.show()

    def stats(source):
        """Return a tuple with raster min, max, and mean.
        """
        if isinstance(source, tuple):
            arr = source[0].read_band(source[1])
        else:
            arr = source
        return Stats(numpy.min(arr), numpy.max(arr), numpy.mean(arr))

    code.interact(
        banner, local=dict(locals(), src=dataset, np=numpy, rio=rasterio))

    return 0
