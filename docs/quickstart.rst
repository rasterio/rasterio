==========
Quickstart
==========

Have a new satellite image or other raster data to dig into? Here are some
examples using an imaginary GeoTIFF file named "rgb.tif".

Opening a dataset
-----------------

First, import rasterio.

.. code-block:: pycon

    >>> import rasterio

Now, open the imaginary file.

.. code-block:: pycon

    >>> dataset = rasterio.open('example.tif')

The ``rasterio.open()`` function behaves like Python's ``open()``. Read
(``'r'``) mode is the default. The response is a dataset object named
``dataset``.

.. code-block:: pycon

    >>> dataset
    <open DatasetReader name='example.tif' mode='r'>

In this case it is an instance of ``DatasetReader``.

Dataset properties
------------------

Properties of the raster dataset in "example.tif" can be accessed through
properties of `dataset`.

.. code-block:: pycon

    >>> dataset.count
    3

Rasters have "bands" and this example has three.

.. code-block:: pycon

    >>> dataset.width, dataset.height
    (791, 718)

Each band is a raster grid 791 cells (or pixels) wide and 718 pixels tall.

.. code-block:: pycon

    >>> dataset.bounds
    BoundingBox(left=101985.0, bottom=2611485.0, right=339315.0, top=2826915.0)

The thing that makes GIS raster data unique is that its pixels are mapped to
some region in the world. Our example covers the world from 101985 meters (in
this case) to 339315 meters, left to right, and 2611485 meters to 2826915
meters bottom to top. It covers a region 237.33 kilometers wide by 215.43
kilometers high.

The ``bounds`` property is derived from a more fundamental property, the
dataset's geospatial ``transform``.

.. code-block:: pycon

    >>> dataset.transform
    Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0)

This is an affine transformation matrix that maps pixel locations in (row, col)
coordinates to (x, y) world coordinates.

But where exactly does the image cover? 101985 meters from where? These
bounding box coordinates are relative to a coordinate reference system (CRS).

.. code-block:: pycon

    >>> dataset.crs
    CRS({'init': 'epsg:32618'})

"epsg:32618" identifies a particular coordinate reference system: UTM zone 18N.
This system is used for mapping areas in the Northern Hemisphere between 72 and
78 degrees west.

Coordinate reference systems are an advanced topic. Suffice it to say that
between the ``crs`` and the ``transform`` a raster dataset is fully
georeferenced and can be compared to other GIS datasets.

Reading raster data
-------------------

TODO.


Writing data
------------

TODO.
