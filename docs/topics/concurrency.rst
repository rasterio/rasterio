Concurrent processing
=====================

Rasterio affords concurrent processing of raster data. Python's global
interpreter lock (GIL) is released when calling GDAL's ``GDALRasterIO()``
function, which means that Python threads can read and write concurrently.

The Numpy library also often releases the GIL, e.g., in applying
universal functions to arrays, and this makes it possible to distribute
processing of an array across cores of a processor. The Cython function
below, included in Rasterio's ``_example`` module, simulates such
a GIL-releasing raster processing function.

.. code-block:: python

    # cython: boundscheck=False

    import numpy as np


    def compute(unsigned char[:, :, :] input):
        """reverses bands inefficiently

        Given input and output uint8 arrays, fakes an CPU-intensive
        computation.
        """
        cdef int I, J, K
        cdef int i, j, k, l
        cdef double val
        I = input.shape[0]
        J = input.shape[1]
        K = input.shape[2]
        output = np.empty((I, J, K), dtype='uint8')
        cdef unsigned char[:, :, :] output_view = output
        with nogil:
            for i in range(I):
                for j in range(J):
                    for k in range(K):
                        val = <double>input[i, j, k]
                        for l in range(2000):
                            val += 1.0
                        val -= 2000.0
                        output_view[~i, j, k] = <unsigned char>val
        return output

Here is the program in examples/thread_pool_executor.py.

.. code-block:: python

    """thread_pool_executor.py

    Operate on a raster dataset window-by-window using a ThreadPoolExecutor.

    Simulates a CPU-bound thread situation where multiple threads can improve
    performance.

    With -j 4, the program returns in about 1/4 the time as with -j 1.
    """

    import concurrent.futures

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

The code above simulates a CPU-intensive calculation that runs faster when
spread over multiple cores using the ``ThreadPoolExecutor`` from Python 3's
``concurrent.futures`` module. Compared to the case of one concurrent job 
(``-j 1``),

.. code-block:: console

   $ time python examples/thread_pool_executor.py tests/data/RGB.byte.tif /tmp/test.tif -j 1

   real    0m3.555s
   user    0m3.422s
   sys     0m0.095s

we get an almost 3x speed up with four concurrent jobs.

.. code-block:: console

   $ time python examples/thread_pool_executor.py tests/data/RGB.byte.tif /tmp/test.tif -j 4

   real    0m1.247s
   user    0m3.505s
   sys     0m0.088s

.. note::

   If the function that you'd like to map over raster windows doesn't release
   the GIL, you can replace ``ThreadPoolExecutor`` with ``ProcessPoolExecutor``
   and get the same results with similar performance.
