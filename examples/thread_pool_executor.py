"""thread_pool_executor.py

Operate on a raster dataset window-by-window using a ThreadPoolExecutor.

Simulates a CPU-bound thread situation where multiple threads can improve
performance.

With -j 4, the program returns in about 1/4 the time as with -j 1.
"""

import concurrent.futures
import multiprocessing
import threading

import rasterio
from rasterio._example import compute


def main(infile, outfile, num_workers=4):
    """Process infile block-by-block and write to a new file

    The output is the same as the input, but with band order
    reversed.
    """

    with rasterio.open(infile) as src:

        # Create a destination dataset based on source params. The
        # destination will be tiled, and we'll process the tiles
        # concurrently.
        profile = src.profile
        profile.update(blockxsize=128, blockysize=128, tiled=True)

        with rasterio.open(outfile, "w", **src.profile) as dst:
            windows = [window for ij, window in dst.block_windows()]

            # We cannot write to the same file from multiple threads
            # without causing race conditions. To safely read/write
            # from multiple threads, we use a lock to protect the
            # DatasetReader/Writer
            read_lock = multiprocessing.Lock()
            write_lock = multiprocessing.Lock()

            def process(window):
                with read_lock:
                    src_array = src.read(window=window)
                result = compute(src_array)
                with write_lock:
                    dst.write(result, window=window)

            # We map the process() function over the list of
            # windows.
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_workers
            ) as executor:
                executor.map(process, windows)


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
