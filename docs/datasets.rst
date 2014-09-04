Datasets and ndarrays
=====================

Dataset objects provide read, read-write, and write access to raster data files
and are obtained by calling ``rasterio.open()``. That function mimics Python's
built-in ``open()`` and the dataset objects it returns mimic Python ``file``
objects.

.. code-block:: pycon

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
systems. The ``driver`` attribute gives you the name of the GDAL format
driver used. The ``height`` and ``width`` are the number of rows and columns of
the raster dataset and ``shape`` is a ``height, width`` tuple as used by
Numpy. The ``count`` attribute tells you the number of bands in the dataset.

.. code-block:: pycon

    >>> dataset.driver
    u'GTiff'
    >>> dataset.height, dataset.width
    (718, 791)
    >>> dataset.shape
    (718, 791)
    >>> dataset.count
    3

What makes geospatial raster datasets different from other raster files is
that their pixels map to regions of the Earth. A dataset has a coordinate
reference system and an affine transformation matrix that maps pixel
coordinates to coordinates in that reference system.

.. code-block:: pycon

    >>> dataset.crs
    {u'units': u'm', u'no_defs': True, u'ellps': u'WGS84', u'proj': u'utm', u'zone': 18}
    >>> dataset.affine
    Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0)

To get the ``x, y`` world coordinates for the upper left corner of any pixel,
take the product of the affine transformation matrix and the tuple ``(col,
row)``.  

.. code-block:: pycon

    >>> col, row = 0, 0
    >>> src.affine * (col, row)
    (101985.0, 2826915.0)
    >>> col, row = src.width, src.height
    >>> src.affine * (col, row)
    (339315.0, 2611485.0)

Reading data
------------

Datasets generally have one or more bands (or layers). Following the GDAL
convention, these are indexed starting with the number 1. The first band of
a file can be read like this:

.. code-block:: pycon

    >>> dataset.read_band(1)
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

.. code-block::

    >>> from matplotlib import pyplot
    >>> pyplot.imshow(dataset.read_band(1), cmap='pink')
    <matplotlib.image.AxesImage object at 0x111195c10>
    >>> pyplot.show()

.. image:: http://farm6.staticflickr.com/5032/13938576006_b99b23271b_o_d.png

The indexes, Numpy data types, and nodata values of all a dataset's bands can
be had from its ``indexes``, ``dtypes``, and ``nodatavals`` attributes.

.. code-block:: pycon

    >>> for i, dtype, ndval in zip(src.indexes, src.dtypes, src.nodatavals):
    ...     print i, dtype, nodataval
    ...
    1 <type 'numpy.uint8'> 0.0
    2 <type 'numpy.uint8'> 0.0
    3 <type 'numpy.uint8'> 0.0

To close a dataset, call its ``close()`` method.

.. code-block:: pycon

    >>> dataset.close()
    >>> dataset
    <closed RasterReader name='tests/data/RGB.byte.tif' mode='r'>

After it's closed, data can no longer be read.

.. code-block:: pycon

    >>> dataset.read_band(1)
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
    ValueError: can't read closed raster file

This is the same behavior as Python's ``file``.

.. code-block:: pycon

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

.. code-block:: pycon

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

Writing data
------------

Opening a file in writing mode is a little more complicated than opening
a text file in Python. The dimensions of the raster dataset, the 
data types, and the specific format must be specified.

.. code-block:: pycon

   >>> with rasterio.oepn

Writing data mostly works as with a Python file. There are a few format-
specific differences. TODO: details.

