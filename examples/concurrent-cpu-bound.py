"""concurrent-cpu-bound.py

Operate on a raster dataset window-by-window using a ThreadPoolExecutor.
"""

import concurrent.futures
import multiprocessing
import time

import rasterio


def process_window(data):
    # Fake an expensive computation.
    time.sleep(0.1)
    return data


def main(infile, outfile, num_workers=4):
    """Use process_window() to process a file in parallel."""

    with rasterio.drivers():

        # Open source dataset.
        with rasterio.open(infile) as src:

            # Create a destination dataset based on source params.
            meta = src.meta
            meta.update(blockxsize=256, blockysize=256)
            meta.update(tiled = 'yes')

            # Create an empty destination file on disk.
            with rasterio.open(outfile, 'w', **meta) as dst:
                
                # Define a generator for 3D array, window pairs.
                def jobs():
                    for ij, window in dst.block_windows(1):
                        yield src.read(window=window), window

                # Submit the jobs to the thread pool executor.
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=num_workers) as executor:
    
                    future_to_window = {
                        executor.submit(process_window, data): window
                        for data, window in jobs()}
    
                    for future in concurrent.futures.as_completed(
                            future_to_window):
                        
                        window = future_to_window[future]

                        data = future.result()
                        for i, arr in enumerate(data, 1):
                            dst.write_band(i, arr, window=window)


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
    
