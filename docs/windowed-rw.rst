Windowed reading and writing
============================

Beginning in rasterio 0.3, you can read and write on "windows" of raster
files.

A window is described in rasterio by a 4 element tuple. The elements are:

0: offset in number of image rows from the dataset's upper left,
1: offset in number of image columns from the dataset's upper left,
2: the number of rows in the window,
3: the number of columns in the window.

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

Writing works similarly. The following creates a blank 100x100 GeoTIFF
and plops 2500 pixels with value 127 into a square window 10 pixels to the
right and 30 pixels down from the upper left corner of the GeoTIFF.

.. code-block:: python

    image = numpy.ones((50, 50), dtype=rasterio.ubyte) * 127
    
    with rasterio.open(
            '/tmp/example.tif', 'w', 
            driver='GTiff', width=100, height=100, count=1,
            dtype=a.dtype) as dst:
        dst.write_band(1, image, window=(30, 10, 50, 50))

