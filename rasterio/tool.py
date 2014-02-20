
import code
import logging
import sys

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('rasterio')


def main(srcfile):
    
    with rasterio.drivers(), rasterio.open(srcfile) as src:
        
        def show(band):
            import matplotlib.pyplot as plt
            plt.imshow(band)
            plt.gray()
            plt.show()
        
        code.interact(
            'Rasterio %s Interactive Inspector (Python %s)\n'
            'Type "src.name", "src.read_band(1)", or "help(src)" '
            'for more information.' %  (
                rasterio.__version__, 
                '.'.join(map(str, sys.version_info[:3]))),
            local=locals())

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

