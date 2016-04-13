"""concurrent-cpu-bound.py

Operate on a raster dataset window-by-window using a ThreadPoolExecutor.

Simulates a CPU-bound thread situation where multiple threads can improve performance.

With -j 4, the program returns in about 1/4 the time as with -j 1.
"""

import concurrent.futures
import multiprocessing
import time

import numpy
import rasterio
from rasterio._example import compute


def main(infile, outfile, num_workers=4):

    with rasterio.drivers():

        # Open the source dataset.
        with rasterio.open(infile) as src:

            # Create a destination dataset based on source params.
            # The destination will be tiled, and we'll "process" the tiles
            # concurrently.
            meta = src.meta
            del meta['transform']
            meta.update(affine=src.affine)
            meta.update(blockxsize=256, blockysize=256, tiled='yes')
            with rasterio.open(outfile, 'w', **meta) as dst:

                # Define a generator for data, window pairs.
                def jobs():
                    for ij, window in dst.block_windows():
                        data = src.read(window=window)
                        result = numpy.zeros(data.shape, dtype=data.dtype)
                        yield data, result, window

                # Submit the jobs to the thread pool executor.
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=num_workers) as executor:

                    # Map the futures returned from executor.submit()
                    # to their destination windows.
                    #
                    # The _example.compute function modifies no Python
                    # objects and releases the GIL. It can execute
                    # concurrently.
                    future_to_window = {
                        executor.submit(compute, data, res): (res, window)
                        for data, res, window in jobs()}

                    # As the processing jobs are completed, get the
                    # results and write the data to the appropriate
                    # destination window.
                    for future in concurrent.futures.as_completed(
                            future_to_window):

                        result, window = future_to_window[future]

                        dst.write(result, window=window)


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser(
        description="Concurrent raster processing demo")
    parser.add_argument(
        'input',
        metavar='INPUT',
        help="Input file name")
    parser.add_argument(
        'output',
        metavar='OUTPUT',
        help="Output file name")
    parser.add_argument(
        '-j',
        metavar='NUM_JOBS',
        type=int,
        default=multiprocessing.cpu_count(),
        help="Number of concurrent jobs")
    args = parser.parse_args()

    main(args.input, args.output, args.j)

