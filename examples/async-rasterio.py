"""async-rasterio.py

Operate on a raster dataset window-by-window using asyncio's event loop
and thread executor.

Simulates a CPU-bound thread situation where multiple threads can improve
performance.
"""

import asyncio
import time

import numpy as np
import rasterio

from rasterio._example import compute

def main(infile, outfile, with_threads=False):
    
    with rasterio.drivers():

        # Open the source dataset.
        with rasterio.open(infile) as src:

            # Create a destination dataset based on source params. The
            # destination will be tiled, and we'll "process" the tiles
            # concurrently.

            meta = src.meta
            del meta['transform']
            meta.update(affine=src.affine)
            meta.update(blockxsize=256, blockysize=256, tiled='yes')
            with rasterio.open(outfile, 'w', **meta) as dst:

                loop = asyncio.get_event_loop()
                
                # With the exception of the ``yield from`` statement,
                # process_window() looks like callback-free synchronous
                # code. With a coroutine, we can keep the read, compute,
                # and write statements close together for
                # maintainability. As in the concurrent-cpu-bound.py
                # example, all of the speedup is provided by
                # distributing raster computation across multiple
                # threads. The difference here is that we're submitting
                # jobs to the thread pool asynchronously.

                @asyncio.coroutine
                def process_window(window):
                    
                    # Read a window of data.
                    data = src.read(window=window)
                    
                    # We run the raster computation in a separate thread
                    # and pause until the computation finishes, letting
                    # other coroutines advance.
                    #
                    # The _example.compute function modifies no Python
                    # objects and releases the GIL. It can execute
                    # concurrently.
                    result = np.zeros(data.shape, dtype=data.dtype)
                    if with_threads:
                        yield from loop.run_in_executor(
                                            None, compute, data, result)
                    else:
                        compute(data, result)
                    
                    dst.write(result, window=window)

                # Queue up the loop's tasks.
                tasks = [asyncio.Task(process_window(window)) 
                         for ij, window in dst.block_windows(1)]
                
                # Wait for all the tasks to finish, and close.
                loop.run_until_complete(asyncio.wait(tasks))
                loop.close()

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
        '--with-workers',
        action='store_true',
        help="Run with a pool of worker threads")
    args = parser.parse_args()
    
    main(args.input, args.output, args.with_workers)

