"""async-rasterio.py

Operate on a raster dataset window-by-window using asyncio's event loop
and thread executor.

Simulates a CPU-bound thread situation where multiple threads can improve
performance.
"""

import asyncio
import time

import rasterio


def main(infile, outfile):
    
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

                loop = asyncio.get_event_loop()
                
                def compute(data):
                    # Fake a CPU-intensive computation.
                    time.sleep(0.1)
                    # Reverse the bands just for fun.
                    return data[::-1]

                # With the exception of the ``yield from`` statement,
                # process_window() looks just good ole synchronous code.
                # With a coroutine, we can keep the read, compute, and
                # write statements close together.
                @asyncio.coroutine
                def process_window(window):
                    # Read a window of data.
                    data = src.read(window=window)
                    
                    # We run the raster computation in a separate
                    # thread and pause until the computation finishes,
                    # letting other coroutines, which run computations
                    # in other threads, advance.
                    result = yield from loop.run_in_executor(
                                            None, compute, data)
                    
                    # Write the result.
                    for i, arr in enumerate(result, 1):
                        dst.write_band(i, arr, window=window)

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
    args = parser.parse_args()
    
    main(args.input, args.output)

