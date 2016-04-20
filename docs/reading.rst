Reading Datasets
=====================

.. todo::

    * use of context manager
    * ndarray shape is (band, cols, rows)
    * Discuss and/or link to topics
        - supported formats, drivers
        - vsi
        - tags
        - profile
        - crs
        - transforms
        - dtypes
        - block windows


Dataset objects provide read, read-write, and write access to raster data files
and are obtained by calling ``rasterio.open()``. That function mimics Python's
built-in ``open()`` and the dataset objects it returns mimic Python ``file``
objects.

.. code-block:: python

    >>> import rasterio
    >>> src = rasterio.open('tests/data/RGB.byte.tif')
    >>> src
    <open RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    >>> src.name
    'tests/data/RGB.byte.tif'
    >>> src.mode
    'r'
    >>> src.closed
    False

If you try to access a nonexistent path, ``rasterio.open()`` does the same
thing as ``open()``, raising an exception immediately.

.. code-block:: python

    >>> open('/lol/wut.tif')
    Traceback (most recent call last):
     ...
    IOError: [Errno 2] No such file or directory: '/lol/wut.tif'
    >>> rasterio.open('/lol/wut.tif')
    Traceback (most recent call last):
     ...
    RasterioIOError: No such file or directory

Datasets generally have one or more bands (or layers). Following the GDAL
convention, these are indexed starting with the number 1. The first band of
a file can be read like this:

.. code-block:: python

    >>> array = src.read(1)
    >>> array.shape
    (718, 791)

The returned object is a 2-dimensional Numpy ndarray. The representation of
that array at the Python prompt is a summary; the GeoTIFF file that
Rasterio uses for testing has 0 values in the corners, but has nonzero values
elsewhere.

.. code-block:: python

    >>> from matplotlib import pyplot
    >>> pyplot.imshow(array, cmap='pink')
    <matplotlib.image.AxesImage object at 0x...>
    >>> pyplot.show()  # doctest: +SKIP


.. image:: http://farm6.staticflickr.com/5032/13938576006_b99b23271b_o_d.png

The indexes, Numpy data types, and nodata values of all a dataset's bands can
be had from its ``indexes``, ``dtypes``, and ``nodatavals`` attributes.

.. code-block:: python

    >>> for i, dtype, nodataval in zip(src.indexes, src.dtypes, src.nodatavals):
    ...     print i, dtype, nodataval
    ...
    1 uint8 0.0
    2 uint8 0.0
    3 uint8 0.0

To close a dataset, call its ``close()`` method.

.. code-block:: python

    >>> src.close()
    >>> src
    <closed RasterReader name='tests/data/RGB.byte.tif' mode='r'>

After it's closed, data can no longer be read.

.. code-block:: python

    >>> src.read(1)
    Traceback (most recent call last):
     ...
    ValueError: can't read closed raster file

This is the same behavior as Python's ``file``.

.. code-block:: python

    >>> f = open('README.rst')
    >>> f.close()
    >>> f.read()
    Traceback (most recent call last):
     ...
    ValueError: I/O operation on closed file

As Python ``file`` objects can, Rasterio datasets can manage the entry into 
and exit from runtime contexts created using a ``with`` statement. This 
ensures that files are closed no matter what exceptions may be raised within
the the block.

.. code-block:: python

    >>> with rasterio.open('tests/data/RGB.byte.tif', 'r') as one:
    ...     with rasterio.open('tests/data/RGB.byte.tif', 'r') as two:
    ...        print two
    ...     print one
    <open RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    <open RasterReader name='tests/data/RGB.byte.tif' mode='r'>

    >>> print two
    <closed RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    >>> print one
    <closed RasterReader name='tests/data/RGB.byte.tif' mode='r'>
