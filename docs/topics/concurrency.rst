Concurrent processing
=====================

Rasterio affords concurrent processing of raster data. The Python GIL is
released when calling GDAL's ``GDALRasterIO()`` function, which means that
datasets can read and write concurrently with other threads.

The Numpy library also releases the GIL as much as it can, e.g., in applying
universal functions to arrays, and this makes it possible to distribute
processing of an array across cores of a processor. The Cython function below,
included in Rasterio's ``_example`` module, simulates such a GIL-releasing
raster processing function.

.. code-block:: python

    # cython: boundscheck=False

    def compute(
            unsigned char[:, :, :] input,
            unsigned char[:, :, :] output):
        # Given input and output uint8 arrays, fakes an CPU-intensive
        # computation.
        cdef int I, J, K
        cdef int i, j, k, l
        cdef double val
        I = input.shape[0]
        J = input.shape[1]
        K = input.shape[2]
        with nogil:
            for i in range(I):
                for j in range(J):
                    for k in range(K):
                        val = <double>input[i, j, k]
                        for l in range(2000):
                            val += 1.0
                        val -= 2000.0
                        output[~i, j, k] = <unsigned char>val

Here is the program in examples/concurrent-cpu-bound.py.

.. code-block:: python

    """concurrent-cpu-bound.py

    Operate on a raster dataset window-by-window using a ThreadPoolExecutor.

    Simulates a CPU-bound thread situation where multiple threads can improve performance.

    With -j 4, the program returns in about 1/4 the time as with -j 1.
    """

    import concurrent.futures
    import multiprocessing

    import numpy as np
    import rasterio
    from rasterio._example import compute


    def main(infile, outfile, num_workers=4):

        with rasterio.Env():

            # Open the source dataset.
            with rasterio.open(infile) as src:

                # Create a destination dataset based on source params.
                # The destination will be tiled, and we'll "process" the tiles
                # concurrently.
                profile = src.profile
                profile.update(blockxsize=256, blockysize=256, tiled=True)
                with rasterio.open(outfile, 'w', **profile) as dst:

                    # Define a generator for data, window pairs.
                    def jobs():
                        for ij, window in dst.block_windows():
                            data = src.read(window=window)
                            result = np.zeros(data.shape, dtype=data.dtype)
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

The code above simulates a fairly CPU-intensive process that runs faster when
spread over multiple cores using the ``ThreadPoolExecutor`` from Python 3's
``concurrent.futures`` module. Compared to the case of one concurrent job 
(``-j 1``)

.. code-block:: console

    $ time python examples/concurrent-cpu-bound.py tests/data/RGB.byte.tif /tmp/threads.tif -j 1

    real    0m3.474s
    user    0m3.426s
    sys     0m0.043s

we get an almost 3x speed up with four concurrent jobs.

.. code-block:: console

    $ time python examples/concurrent-cpu-bound.py tests/data/RGB.byte.tif /tmp/threads.tif -j 4

    real    0m1.335s
    user    0m3.400s
    sys     0m0.043s
