Datasets and ndarrays
=====================

Dataset objects provide read, read-write, and write access to raster data files
and are obtained by calling ``rasterio.open()``. That function mimics Python's
built-in ``open()`` and dataset objects mimic Python ``file`` objects.

.. code-block:: pycon

    >>> import rasterio
    >>> dataset = rasterio.open('rasterio/tests/data/RGB.byte.tif')
    >>> print dataset
    <open RasterReader name='rasterio/tests/data/RGB.byte.tif' mode='r'>
    >>> dataset.name
    'rasterio/tests/data/RGB.byte.tif'
    >>> print dataset.mode
    r
    >>> print dataset.closed
    False

If you attempt to open a nonexistent dataset, ``rasterio.open()`` does the same
thing as ``open()``: raising an exception immediately.

.. code-block:: pycon

    >>> open('/lol/wut.tif')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    IOError: [Errno 2] No such file or directory: '/lol/wut.tif'
    >>> rasterio.open('/lol/wut.tif')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    IOError: no such file or directory: '/lol/wut.tif'

Datasets generally have one or more bands (or layers) and these are indexed starting with the number 1. The first band of a file can be read like this:

.. code-block:: pycon

    >>> dataset.read_band(1)
    array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint8)

The returned object is a Numpy (N-dimensional; 2 in this case) ndarry.

indexes of all a dataset's bands can be had from a dataset's ``indexes``
attribute. Read all band data from a dataset like this:

.. code-block:: pycon

    >>> dataset.indexes
    [1, 2, 3]
    >>> [dataset.read_band(i) for i in dataset.indexes]
    [array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint8),
     array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint8),
     array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint8)]

