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

The code above simulates a CPU-intensive calculation that runs faster when
spread over multiple cores using the ``ThreadPoolExecutor`` from Python 3's
``concurrent.futures`` module. Compared to the case of one concurrent job 
(``-j 1``),

.. code-block:: console

   $ time python examples/thread_pool_executor.py tests/data/RGB.byte.tif /tmp/test.tif -j 1

   real    TODO
   user    TODO
   sys     TODO

we get an almost 3x speed up with four concurrent jobs.

.. code-block:: console

   $ time python examples/thread_pool_executor.py tests/data/RGB.byte.tif /tmp/test.tif -j 4

   real    TODO
   user    TODO
   sys     TODO

If the function that you'd like to map over raster windows doesn't release the 
GIL, you unfortunately cannot simply replace ``ThreadPoolExecutor`` with 
``ProcessPoolExecutor``, the DatasetReader/Writer cannot be shared by multiple
processes, which means that each process needs to open the file seperately,
or you can do all the reading and writing from the main thread, as shown in this 
next example. This is much less efficient memory wise, however.

.. code-block:: python
    arrays = [src.read(window=window) for window in windows]

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=num_workers
    ) as executor:
        futures = executor.map(compute, arrays)
        for window, result in zip(windows, futures):
            dst.write(result, window=window)

.. note::
    If you wish to do multiprocessing accross very large images that do not fit in memory,
    of you wish to do multiprocessing across multiple machines. You might want to have a 
    look at `dask <https://dask.org/>`__ and in particular this 
    `example <https://examples.dask.org/applications/satellite-imagery-geotiff.html>`__.