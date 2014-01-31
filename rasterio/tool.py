
import code
import logging
import pprint
import sys

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger('rasterio')


def main(srcfile):
    
    with rasterio.drivers(), rasterio.open(srcfile) as src:
            
        code.interact(
            'Rasterio %s Interactive Interpreter\n'
            'Type "src.name", "src.read_band(1)", or "help(src)" '
            'for more information.' %  rasterio.__version__,
            local=locals())


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

