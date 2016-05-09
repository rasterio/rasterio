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
following functions to convert between raster and image axis order:

.. code:: python

    def reshape_as_image(arr):
        """raster order (bands, rows, cols) -> image (rows, cols, bands)
        """
        return np.swapaxes(np.swapaxes(arr, 0, 2), 0, 1)


    def reshape_as_raster(arr):
        """image order (rows, cols, bands) -> rasterio (bands, rows, cols)
        """
        return np.swapaxes(np.swapaxes(arr, 2, 0), 2, 1)

