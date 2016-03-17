Reading Datasets
=====================


Dataset objects provide read, read-write, and write access to raster data files
and are obtained by calling ``rasterio.open()``. That function mimics Python's
built-in ``open()`` and the dataset objects it returns mimic Python ``file``
objects.

.. code-block:: python

    >>> import rasterio
    >>> dataset = rasterio.open('tests/data/RGB.byte.tif')
    >>> dataset
    <open RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    >>> dataset.name
    'tests/data/RGB.byte.tif'
    >>> dataset.mode
    r
    >>> dataset.closed
    False

If you attempt to access a nonexistent path, ``rasterio.open()`` does the same
thing as ``open()``, raising an exception immediately.

.. code-block:: python

    >>> open('/lol/wut.tif')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    IOError: [Errno 2] No such file or directory: '/lol/wut.tif'
    >>> rasterio.open('/lol/wut.tif')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    IOError: no such file or directory: '/lol/wut.tif'

Reading data
------------

.. todo::

    drivers
    vsi (link)
    context manager
    ndarray = [band, cols, rows]
    tags
    profile
    crs
    transforms
    dtypes
    block windows

Datasets generally have one or more bands (or layers). Following the GDAL
convention, these are indexed starting with the number 1. The first band of
a file can be read like this:

.. code-block:: python

    >>> dataset.read(1)
    array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint8)

The returned object is a 2-dimensional Numpy ndarray. The representation of
that array at the Python prompt is just a summary; the GeoTIFF file that
Rasterio uses for testing has 0 values in the corners, but has nonzero values
elsewhere.

.. code-block:: python

    >>> from matplotlib import pyplot
    >>> pyplot.imshow(dataset.read(1), cmap='pink')
    <matplotlib.image.AxesImage object at 0x111195c10>
    >>> pyplot.show()

.. image:: http://farm6.staticflickr.com/5032/13938576006_b99b23271b_o_d.png

The indexes, Numpy data types, and nodata values of all a dataset's bands can
be had from its ``indexes``, ``dtypes``, and ``nodatavals`` attributes.

.. code-block:: python

    >>> for i, dtype, ndval in zip(src.indexes, src.dtypes, src.nodatavals):
    ...     print i, dtype, nodataval
    ...
    1 <type 'numpy.uint8'> 0.0
    2 <type 'numpy.uint8'> 0.0
    3 <type 'numpy.uint8'> 0.0

To close a dataset, call its ``close()`` method.

.. code-block:: python

    >>> dataset.close()
    >>> dataset
    <closed RasterReader name='tests/data/RGB.byte.tif' mode='r'>

After it's closed, data can no longer be read.

.. code-block:: python

    >>> dataset.read(1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ValueError: can't read closed raster file

This is the same behavior as Python's ``file``.

.. code-block:: python

    >>> f = open('README.rst')
    >>> f.close()
    >>> f.read()
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ValueError: I/O operation on closed file

As Python ``file`` objects can, Rasterio datasets can manage the entry into 
and exit from runtime contexts created using a ``with`` statement. This 
ensures that files are closed no matter what exceptions may be raised within
the the block.

.. code-block:: python

    >>> with rasterio.open('tests/data/RGB.byte.tif', 'r') as one:
    ...     with rasterio.open('tests/data/RGB.byte.tif', 'r') as two:
                print two
    ... print one
    ... print two
    >>> print one
    <open RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    <open RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    <closed RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    <closed RasterReader name='tests/data/RGB.byte.tif' mode='r'>
