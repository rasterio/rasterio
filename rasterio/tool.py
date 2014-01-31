
import code
import pprint

import rasterio

def main(srcfile):
    
    with rasterio.drivers():

        with rasterio.open(srcfile) as src:
            
            code.interact(
                'Rasterio Interactive Interpreter\n'
                'Type "src.name", "src.read_band(1)", or "help(src)" for more information',
                local=locals())


if __name__ == '__main__':
    
    import argparse

    parser = argparse.ArgumentParser(
        description="Open a dataset and drop into an interactive interpreter")
    parser.add_argument(
        'src', 
        metavar='INPUT', 
        help="Input file names")
    args = parser.parse_args()
    
    main(args.src)

