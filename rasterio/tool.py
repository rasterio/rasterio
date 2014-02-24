
import code
import collections
import logging
import sys

import numpy

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('rasterio')

Stats = collections.namedtuple('Stats', ['min', 'max', 'mean'])

def main(srcfile):
    
    with rasterio.drivers(), rasterio.open(srcfile) as src:
        
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
            'Rasterio %s Interactive Inspector (Python %s)\n'
            'Type "src.meta", "src.read_band(1)", or "help(src)" '
            'for more information.' %  (
                rasterio.__version__, 
                '.'.join(map(str, sys.version_info[:3]))),
            local=dict(
                    locals(), np=numpy, rio=rasterio))
    
    return 1

if __name__ == '__main__':
    
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m rasterio.tool",
        description="Open a dataset and drop into an interactive interpreter")
    parser.add_argument(
        'src', 
        metavar='FILE', 
        help="Input dataset file name")
    args = parser.parse_args()
    
    main(args.src)

