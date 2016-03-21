Working with Datasets
======================

.. todo::

    * working with ndarrays
    * src.profile

Attributes
----------

In addition to the file-like attributes shown above, a dataset has a number
of other read-only attributes that help explain its role in spatial information
systems. The ``driver`` attribute gives you the name of the GDAL format
driver used. The ``height`` and ``width`` are the number of rows and columns of
the raster dataset and ``shape`` is a ``height, width`` tuple as used by
Numpy. The ``count`` attribute tells you the number of bands in the dataset.

.. code-block:: python

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

.. code-block:: python

    >>> dataset.crs
    {u'units': u'm', u'no_defs': True, u'ellps': u'WGS84', u'proj': u'utm', u'zone': 18}
    >>> dataset.affine
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

