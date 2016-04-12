Working with Datasets
======================

.. todo::

    * working with ndarrays

Attributes
----------

In addition to the file-like attributes shown above, a dataset has a number
of other read-only attributes that help explain its role in spatial information
systems. The ``driver`` attribute gives you the name of the GDAL format
driver used. The ``height`` and ``width`` are the number of rows and columns of
the raster dataset and ``shape`` is a ``height, width`` tuple as used by
Numpy. The ``count`` attribute tells you the number of bands in the dataset.

.. code-block:: python

    >>> import rasterio
    >>> src = rasterio.open("tests/data/RGB.byte.tif")
    >>> src.driver
    u'GTiff'
    >>> src.height, src.width
    (718, 791)
    >>> src.shape
    (718, 791)
    >>> src.count
    3

What makes geospatial raster datasets different from other raster files is
that their pixels map to regions of the Earth. A dataset has a coordinate
reference system and an affine transformation matrix that maps pixel
coordinates to coordinates in that reference system.

.. code-block:: python

    >>> src.crs
    {'init': u'epsg:32618'}
    >>> src.affine
    Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0)

To get the ``x, y`` world coordinates for the upper left corner of any pixel,
take the product of the affine transformation matrix and the tuple ``(col,
row)``.  

.. code-block:: python

    >>> col, row = 0, 0
    >>> src.affine * (col, row)
    (101985.0, 2826915.0)
    >>> col, row = src.width, src.height
    >>> src.affine * (col, row)
    (339315.0, 2611485.0)


Profile
-------
The ``src.profile`` property is the union of meta, creation options saved as tags, and tiling options.
The primary use of profile is to provide a canonical way of creating a dataset clone, 
encapsulating all the necessary metadata required to recreate a dataset::

    with rasterio.open('example.tif') as src:
        with rasterio.open('clone.tif', 'w', **src.profile) as dst:
            dst.write(src.read()) 

A common pattern for using the profile is to copy a source profile, update it slightly 
to reflect any changes, and use the updated copy to create the output::

    # we start with the profile of the source file
    profile = src.profile.copy()

    # but then change the band count to 1, set the
    # dtype to uint8, and specify LZW compression.
    profile.update(
        dtype=rasterio.uint8,
        count=1,
        compress='lzw')

    # And use the updated profile as kwargs for our destination file
    with open('destination.tif', 'w', **profile) as dst:
        ...
