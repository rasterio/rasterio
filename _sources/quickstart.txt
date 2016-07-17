==========
Quickstart
==========

Have a new satellite image or other raster data to dig into? Here are some
examples using an imaginary GeoTIFF file named "example.tif".

Opening a dataset
-----------------

First, import rasterio.

.. code-block:: pycon

    >>> import rasterio

Now, open the file.

.. code-block:: pycon

    >>> dataset = rasterio.open('example.tif')

The ``rasterio.open()`` function behaves like Python's ``open()``. Read
(``'r'``) mode is the default. The response is a dataset object named
``dataset``.

.. code-block:: pycon

    >>> dataset
    <open DatasetReader name='example.tif' mode='r'>

In this case it is an instance of ``DatasetReader``. Dataset objects have
some of the same properties as Python file objects.

.. code-block:: pycon

    >>> dataset.name
    'example.tif'
    >>> dataset.mode
    'r'
    >>> dataset.closed
    False

Dataset properties
------------------

Properties of the raster data stored in "example.tif" can be accessed through
properties of `dataset`.

.. code-block:: pycon

    >>> dataset.count
    3

Rasters have "bands" and this example has three.

.. code-block:: pycon

    >>> dataset.width, dataset.height
    (791, 718)

Each example band is a raster array with 791 columns and 718 rows.

.. code-block:: pycon

    >>> dataset.dtypes
    ('uint8', 'uint8', 'uint8')

The raster grids contain unsigned 8-bit integer values. The GeoTIFF format
also supports signed integers and floats of different size.

The thing that makes GIS raster data unique is that its pixels are mapped to
some region in the world.

.. code-block:: pycon

    >>> dataset.bounds
    BoundingBox(left=101985.0, bottom=2611485.0, right=339315.0, top=2826915.0)

Our example covers the world from 101985 meters (in this case) to 339315
meters, left to right, and 2611485 meters to 2826915 meters bottom to top. It
covers a region 237.33 kilometers wide by 215.43 kilometers high.

The ``bounds`` property is derived from a more fundamental property: the
dataset's geospatial ``transform``.

.. code-block:: pycon

    >>> dataset.transform
    Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0)

This is an affine transformation matrix that maps pixel locations in (row, col)
coordinates to (x, y) spatial positions. The product of this matrix and ``(0,
0)``, the row and column coordinates of the upper left corner of the dataset,
is the spatial position of the upper left corner.

.. code-block:: pycon

    >>> dataset.transform * (0, 0)
    (101985.0, 2826915.0)

The position of the lower right corner is obtained similarly.

.. code-block:: pycon

    >>> dataset.transform * (dataset.width, dataset.height)
    (339315.0, 2611485.0)

But where exactly does the image cover? 101985 meters from where? These
bounding box coordinates are relative to a coordinate reference system (CRS).

.. code-block:: pycon

    >>> dataset.crs
    CRS({'init': 'epsg:32618'})

"epsg:32618" identifies a particular coordinate reference system: `UTM
<https://en.wikipedia.org/wiki/Universal_Transverse_Mercator_coordinate_system>`__
zone 18N.  This system is used for mapping areas in the Northern Hemisphere
between 72 and 78 degrees west. The upper left corner of the example dataset,
``(101985.0, 2826915.0)``, is 398 kilometers west of zone 18's central meridian
(75 degrees west) and 2827 kilometers north of the equator.

Coordinate reference systems are an advanced topic. Suffice it to say that
between the ``crs`` and the ``transform`` a raster dataset is geo-referenced
and can be compared to other GIS datasets.

.. image:: img/RGB.byte.jpg

The example raster covers the Bahamas.

Reading raster data
-------------------

How can the pixels of a raster band be accessed? By calling ``dataset.read()``
with one of the values from ``dataset.indexes``.

.. code-block:: pycon

    >>> dataset.indexes
    (1, 2, 3)
    >>> band_one = dataset.read(1)

By GDAL convention, bands are indexed from 1.

.. code-block:: pycon

    >>> band_one
    array([[0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           ...,
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0],
           [0, 0, 0, ..., 0, 0, 0]], dtype=uint8)

A Numpy N-D array is returned by ``read()``. Notice in the image shown above
that the dataset has a trapezoid of valid data pixels and a collar of invalid
or "no data" pixels. The no data pixels can be masked when reading using a
keyword argument.

.. code-block:: pycon

    >>> band_one = dataset.read(1, masked=True)
    >>> band_one
    masked_array(data =
     [[-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     ...,
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]],
                 mask =
     [[ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     ...,
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]],
           fill_value = 0)

.. code-block:: pycon

    >>> band_one.min(), band_one.mean(), band_one.max()
    (1, 44.434478650699106, 255)

Calculations on such a masked array do not consider the invalid pixels.

Writing data
------------

TODO.
