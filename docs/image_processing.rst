Interoperability
****************

Image processing software
-------------------------
Some python image processing software packages
organize arrays differently than rasterio. The interpretation of a
3-dimension array read from ``rasterio`` is::

    (bands, rows, columns)

while image processing software like ``scikit-image``, ``pillow`` and ``matplotlib`` are generally ordered::

    (rows, columns, bands)

The number of rows defines the dataset's height, the columns are the dataset's width.

Numpy provides a way to efficiently swap the axis order and you can use the
following reshape functions to convert between raster and image axis order:

.. code:: python

    >>> import rasterio
    >>> from rasterio.plot import reshape_as_raster, reshape_as_image

    >>> raster = rasterio.open("tests/data/RGB.byte.tif").read()
    >>> raster.shape
    (3, 718, 791)

    >>> image = reshape_as_image(raster)
    >>> image.shape
    (718, 791, 3)

    >>> raster2 = reshape_as_raster(image)
    >>> raster2.shape
    (3, 718, 791)

