#!/usr/bin/env python

"""Rasterio interactive dataset inspector"""

import argparse
import logging
import pprint
import sys
import warnings

import rasterio
from rasterio.tool import main


warnings.simplefilter('default')


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(
        prog="rio_insp",
        description="Open a dataset and drop into an interactive interpreter")
    parser.add_argument(
        'src',
        metavar='FILE',
        help="Input dataset file name")
    parser.add_argument(
        '-m', '--mode',
        metavar='MODE',
        type=str,
        default='r',
        help="File mode ('r' or 'r+')")
    parser.add_argument(
        '--meta',
        action='store_true',
        help="Pretty print the dataset's meta properties and exit")
    parser.add_argument(
        '--tags',
        nargs='?',
        default=None,
        const='',
        type=str,
        help="Pretty print the dataset's tags and exit")
    parser.add_argument(
        '--indent',
        default=2,
        type=int,
        metavar='N',
        help="Indentation level for pretty printed output")
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help="Increase verbosity")
    parser.add_argument(
        '-q', '--quiet',
        action='count',
        default=0,
        help="Decrease verbosity")

    args = parser.parse_args()

    verbosity = args.verbose - args.quiet
    log_level = max(10, 30 - 10*verbosity)
    logging.basicConfig(stream=sys.stderr, level=log_level)
    logger = logging.getLogger('rio_insp')

    try:
        with rasterio.drivers(CPL_DEBUG=verbosity>2):
            with rasterio.open(args.src, args.mode) as src:
                if args.meta:
                    pprint.pprint(src.meta, indent=args.indent)
                elif args.tags is not None:
                    if not args.tags:
                        tag_ns = None
                    else:
                        tag_ns = args.tags
                    pprint.pprint(src.tags(ns=tag_ns), indent=args.indent)
                else:
                    main(
                        "Rasterio %s Interactive Inspector (Python %s)\n"
                        'Type "src.meta", "src.read_band(1)", or "help(src)" '
                        'for more information.' %  (
                            rasterio.__version__,
                            '.'.join(map(str, sys.version_info[:3]))),
                        src)
        sys.exit(0)
    except Exception:
        logger.exception("Failed. Exception caught")
        sys.exit(1)

