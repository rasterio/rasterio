Interoperability
****************

Image processing software
-------------------------
Some python image processing software packages
organize arrays differently than rasterio. The interpretation of a
3-dimension array read from ``rasterio`` is::

    (bands, columns, rows)

while image processing software like ``scikit-image`` is often::

    (columns, rows, bands)

Numpy provides a function to efficient swap the axis order:

.. code:: python

    # rasterio (bands, cols, rows) -> skimage (cols, rows, bands)
    image_array = np.swapaxes(array, 0, 2)

    # work in skimage

    # skimage (cols, rows, bands) -> rasterio (bands, cols, rows)
    array = np.swapaxes(image_array, 2, 0)

