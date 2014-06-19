Concurrent processing
=====================

Rasterio affords concurrent processing of raster data. The Python GIL is
released when calling GDAL's ``GDALRasterIO()`` function, which means that
datasets can read and write concurrently with other threads.

The Numpy library also releases the GIL as much as it can, e.g., in applying
universal functions to arrays, and this makes it possible to distribute
processing of an array across cores of a processor.

The program in examples/concurrent-cpu-bound.py

.. code-block:: python

    """concurrent-cpu-bound.py
    
    Operate on a raster dataset window-by-window using a ThreadPoolExecutor.
    
    Simulates a CPU-bound thread situation where multiple threads can improve performance.
    
    With -j 4, the program returns in about 1/4 the time as with -j 1.
    """
    
    import concurrent.futures
    import multiprocessing
    import time
    
    import rasterio
    
    
    def process_window(data):
        # Fake an expensive computation.
        time.sleep(0.1)
        # Reverse the bands just for fun.
        return data[::-1]
    
    
    def main(infile, outfile, num_workers=4):
        """Use process_window() to process a file in parallel."""
    
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
                    # We use the new read() method here to a 3D array with all
                    # bands, but could also use read_band().
                    def jobs():
                        for ij, window in dst.block_windows(1):
                            yield src.read(window=window), window
    
                    # Submit the jobs to the thread pool executor.
                    with concurrent.futures.ThreadPoolExecutor(
                            max_workers=num_workers) as executor:
    
                        # Map the futures returned from executor.submit()
                        # to their destination windows.
                        future_to_window = {
                            executor.submit(process_window, data): window
                            for data, window in jobs()}
    
                        # As the processing jobs are completed, get the
                        # results and write the data to the appropriate
                        # destination window.
                        for future in concurrent.futures.as_completed(
                                future_to_window):
    
                            window = future_to_window[future]
    
                            data = future.result()
    
                            # Since there's no multiband write() method yet in
                            # Rasterio, we use write_band for each part of the
                            # 3D data array.
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

simulates a fairly time-consuming process that runs faster when spread over
multiple cores using the ``ThreadPoolExecutor`` from Python 3's 
``concurrent.futures`` module. Compared to the case of one concurrent job
(``-j 1``)

.. code-block:: console

    $ time python examples/concurrent-cpu-bound.py rasterio/tests/data/RGB.byte.tif /tmp/foo.tif -j 1
    
    real    0m1.415s
    user    0m0.179s
    sys     0m0.039s

we get an almost 3x speed up with four concurrent jobs.

.. code-block:: console

    $ time python examples/concurrent-cpu-bound.py rasterio/tests/data/RGB.byte.tif /tmp/foo.tif -j 4
    
    real    0m0.495s
    user    0m0.171s
    sys     0m0.037s

