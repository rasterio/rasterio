"""thread_pool_executor.py

Operate on a raster dataset window-by-window using a ThreadPoolExecutor.

Simulates a CPU-bound thread situation where multiple threads can improve
performance.

With -j 4, the program returns in about 1/4 the time as with -j 1.
"""

import concurrent.futures
import multiprocessing

import rasterio
from rasterio._example import compute


def main(infile, outfile, num_workers=4):
    """Process infile block-by-block and write to a new file

    The output is the same as the input, but with band order
    reversed.
    """

    with rasterio.Env():

        with rasterio.open(infile) as src:

            # Create a destination dataset based on source params. The
            # destination will be tiled, and we'll process the tiles
            # concurrently.
            profile = src.profile
            profile.update(blockxsize=128, blockysize=128, tiled=True)

            with rasterio.open(outfile, "w", **profile) as dst:

                # Materialize a list of destination block windows
                # that we will use in several statements below.
                windows = [window for ij, window in dst.block_windows()]

                # This generator comprehension gives us raster data
                # arrays for each window. Later we will zip a mapping
                # of it with the windows list to get (window, result)
                # pairs.
                data_gen = (src.read(window=window) for window in windows)

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=num_workers
                ) as executor:

                    # We map the compute() function over the raster
                    # data generator, zip the resulting iterator with
                    # the windows list, and as pairs come back we
                    # write data to the destination dataset.
                    for window, result in zip(
                        windows, executor.map(compute, data_gen)
                    ):
                        dst.write(result, window=window)


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Concurrent raster processing demo")
    parser.add_argument("input", metavar="INPUT", help="Input file name")
    parser.add_argument("output", metavar="OUTPUT", help="Output file name")
    parser.add_argument(
        "-j",
        metavar="NUM_JOBS",
        type=int,
        default=multiprocessing.cpu_count(),
        help="Number of concurrent jobs",
    )
    args = parser.parse_args()

    main(args.input, args.output, args.j)
