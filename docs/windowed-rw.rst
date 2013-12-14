Windowed reading and writing
============================

Beginning in rasterio 0.3, you can read and write "windows" of raster
files.

A window is described in rasterio by a pair of range tuples.

.. code-block:: python

    ((row_start, row_stop), (col_start, col_stop))

The first pair contains the indexes of the raster rows at which the window
starts and stops. The second contains the indexes of the raster columns at
which the window starts and stops. For example,

.. code-block:: python

    ((0, 4), (0, 4))

Specifies a 4 x 4 window at the upper left corner of a raster dataset and

.. code-block:: python

    ((10, 30), (10, 30))

specifies a 20 x 20 window with origin at row 10 and column 10. Use of `None`
for a range value indicates either 0 (for start) or the full raster height or
width (for stop). For example,

.. code-block:: python

    ((None, 4), (None, 4))

also specifies a 4 x 4 window at the upper left corner of the raster and

.. code-block:: python

    ((4, None), (4, None))

specifies a rectangular subset with upper left at row 4, column 4 and
extending to the lower right corner of the raster dataset.

This window syntax mirrors that of Python's range() and slice() functions.

Here is a reading example:

.. code-block:: python

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        roff, coff = 100, 100
        rows, cols = 100, 100
        window = (roff, coff, rows, cols)
        r = src.read_band(1, window=window)

    print(r.shape)
    # output:
    # (100, 100)

Writing works similarly. The following creates a blank 100x100 GeoTIFF and
plops 2500 pixels with value 127 into a square window 30 pixels down from and
10 pixels to the right of the upper left corner of the GeoTIFF.

.. code-block:: python

    image = numpy.ones((50, 50), dtype=rasterio.ubyte) * 127
    
    with rasterio.open(
            '/tmp/example.tif', 'w', 
            driver='GTiff', width=100, height=100, count=1,
            dtype=a.dtype) as dst:
        dst.write_band(1, image, window=(30, 10, 50, 50))

