Datasets and ndarrays
=====================

Dataset objects provide read, read-write, and write access to raster data files
and are obtained by calling ``rasterio.open()``. That function mimics Python's
built-in ``open()`` and the dataset objects it returns mimic Python ``file``
objects.

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

If you attempt to access a nonexistent path, ``rasterio.open()`` does the same
thing as ``open()``, raising an exception immediately.

.. code-block:: pycon

    >>> open('/lol/wut.tif')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    IOError: [Errno 2] No such file or directory: '/lol/wut.tif'
    >>> rasterio.open('/lol/wut.tif')
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    IOError: no such file or directory: '/lol/wut.tif'

Attributes
----------

In addition to the file-like attributes shown above, a dataset has a number
of other read-only attributes that help explain its role in spatial information
systems.

.. code-block:: pycon

    >>> dataset.driver
    u'GTiff'
    >>> dataset.shape
    (718, 791)
    >>> dataset.height, dataset.width
    (718, 791)
    >>> dataset.shape
    (718, 791)
    >>> dataset.transform
    [101985.0, 300.0379266750948, 0.0, 2826915.0, 0.0, -300.041782729805]
    >>> dataset.crs
    {u'units': u'm', u'no_defs': True, u'ellps': u'WGS84', u'proj': u'utm', u'zone': 18}

.. code-block:: pycon

    >>> dataset.count
    3
    >>> dataset.dtypes
    [<type 'numpy.uint8'>, <type 'numpy.uint8'>, <type 'numpy.uint8'>]
    >>> dataset.nodatavals
    [0.0, 0.0, 0.0]

Reading data
------------

Datasets generally have one or more bands (or layers) and these are indexed
starting with the number 1. The first band of a file can be read like this:

.. code-block:: pycon

    >>> dataset.read_band(1)
    array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint8)

The returned object is a Numpy (N-dimensional; N=2 in this case) ndarray. The
GeoTIFF file that Rasterio uses for testing has 0 values in the corners:

.. code-block::

    >>> from matplotlib import pyplot
    >>> pyplot.imshow(dataset.read_band(1), cmap='pink')
    <matplotlib.image.AxesImage object at 0x111195c10>
    >>> pyplot.show()

.. image:: http://farm6.staticflickr.com/5032/13938576006_b99b23271b_o_d.png

Get all indexes of all a dataset's bands can be had from its ``indexes``
attribute and read all band data like this:

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

To close a dataset, call its ``close()`` method.

.. code-block:: pycon

    >>> dataset.close()
    >>> dataset
    <closed RasterReader name='rasterio/tests/data/RGB.byte.tif' mode='r'>

After it's closed, data can no longer be read.

.. code-block:: pycon

    >>> dataset.read_band(1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ValueError: can't read closed raster file

A Python ``file`` has the same behavior.

.. code-block:: pycon

    >>> f = open('README.rst')
    >>> f.close()
    >>> f.read()
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ValueError: I/O operation on closed file

As Python ``file`` objects can, Rasterio datasets can manage the entry into 
and exit from runtime contexts created using a ``with`` statement.

.. code-block:: pycon

    >>> with rasterio.open('rasterio/tests/data/RGB.byte.tif', 'r') as one:
    ...     with rasterio.open('rasterio/tests/data/RGB.byte.tif', 'r') as two:
                print two
    ... print one
    ... print two
    >>> print one
    <open RasterReader name='rasterio/tests/data/RGB.byte.tif' mode='r'>
    <open RasterReader name='rasterio/tests/data/RGB.byte.tif' mode='r'>
    <closed RasterReader name='rasterio/tests/data/RGB.byte.tif' mode='r'>
    <closed RasterReader name='rasterio/tests/data/RGB.byte.tif' mode='r'>
