Windowed reading and writing
============================

Beginning in rasterio 0.3, you can read and write "windows" of raster files.
This feature allows you to operate on rasters that are larger than your
computers RAM or process chunks of very large rasters in parallel.

Windows
-------

A window is a view onto a rectangular subset of a raster dataset and is
described in rasterio by a pair of range tuples.

.. code-block:: python

    ((row_start, row_stop), (col_start, col_stop))

The first pair contains the indexes of the raster rows at which the window
starts and stops. The second contains the indexes of the raster columns at
which the window starts and stops. For example,

.. code-block:: python

    ((0, 4), (0, 4))

Specifies a 4 x 4 window at the upper left corner of a raster dataset and

.. code-block:: python

    ((10, 20), (10, 20))

specifies a 10 x 10 window with origin at row 10 and column 10. Use of `None`
for a range value indicates either 0 (in the start position) or the full raster
height or width (in the stop position). The window tuple

.. code-block:: python

    ((None, 4), (None, 4))

also specifies a 4 x 4 window at the upper left corner of the raster and

.. code-block:: python

    ((4, None), (4, None))

specifies a rectangular subset with upper left at row 4, column 4 and
extending to the lower right corner of the raster dataset.

Using window tuples should feel like using Python's range() and slice()
functions. 

.. code-block:: pycon

    >>> range(10, 20)
    [10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    >>> range(10, 20)[slice(4, None)]
    [14, 15, 16, 17, 18, 19]

Reading
-------

Here is an example of reading a 100 row x 100 column subset of the rasterio
test file.

.. code-block:: pycon

    >>> import rasterio
    >>> with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    ...     w = src.read_band(1, window=((0, 100), (0, 100)))
    ...
    >>> print(w.shape)
    (100, 100)

Writing
-------

Writing works similarly. The following creates a blank 500 column x 300 row
GeoTIFF and plops 37500 pixels with value 127 into a window 30 pixels down from
and 50 pixels to the right of the upper left corner of the GeoTIFF.

.. code-block:: python

    image = numpy.ones((150, 250), dtype=rasterio.ubyte) * 127
    
    with rasterio.open(
            '/tmp/example.tif', 'w',
            driver='GTiff', width=500, height=300, count=1,
            dtype=image.dtype) as dst:
        dst.write_band(1, image, window=((30, 180), (50, 300)))
    
The result:

.. image:: http://farm6.staticflickr.com/5503/11378078386_cbe2fde02e_o_d.png
   :width: 500
   :height: 300

Decimation
----------

If the write window is smaller than the data, the data will be decimated.
Below, the window is scaled to one third of the source image.

.. code-block:: python

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        r = src.read_band(1)
        g = src.read_band(2)
        b = src.read_band(3)
    
    window = (30, 269), (50, 313)
    
    with rasterio.open(
            '/tmp/example.tif', 'w',
            driver='GTiff', width=500, height=300, count=3,
            dtype=r.dtype) as dst:
        dst.write_band(1, r, window=window) 
        dst.write_band(2, g, window=window)
        dst.write_band(3, b, window=window)

And the result:

.. image:: http://farm4.staticflickr.com/3804/11378361126_c034743079_o_d.png
   :width: 500
   :height: 300

Advanced windows
----------------

Since windows are like slices, you can also use negative numbers in rasterio
windows.

.. code-block:: python

    ((-4, None), (-4, None))

specifies a 4 x 4 rectangular subset with upper left at 4 rows to the left of
and 4 columns above the lower right corner of the dataset and extending to the
lower right corner of the dataset.

Below is an example of reading a raster subset and then writing it into a 
larger subset that is defined relative to the lower right corner of the
destination dataset.

.. code-block:: python

    read_window = (350, 410), (350, 450)
    
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        r = src.read_band(1, window=read_window)
        g = src.read_band(2, window=read_window)
        b = src.read_band(3, window=read_window)
    
    write_window = (-240, None), (-400, None)
    
    with rasterio.open(
            '/tmp/example2.tif', 'w',
            driver='GTiff', width=500, height=300, count=3,
            dtype=r.dtype) as dst:
        dst.write_band(1, r, window=write_window) 
        dst.write_band(2, g, window=write_window)
        dst.write_band(3, b, window=write_window)

This example also demonstrates decimation.

.. image:: http://farm3.staticflickr.com/2827/11378772013_c8ab540f21_o_d.png
   :width: 500
   :height: 300

Blocks
------

Raster datasets are generally composed of multiple blocks of data and
windowed reads and writes are most efficient when the windows match the
dataset's own block structure. When a file is opened to read, the shape
of blocks for any band can be had from the block_shapes property.

.. code-block:: pycon

    >>> with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    ...     for i, shape in enumerate(src.block_shapes, 1):
    ...         print(i, shape)
    ...
    (1, (3, 791))
    (2, (3, 791))
    (3, (3, 791))


The block windows themselves can be had from the block_windows function.

.. code-block:: pycon

    >>> with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
    ...     for ji, window in src.block_windows(1):
    ...         print(ji, window)
    ...
    ((0, 0), ((0, 3), (0, 791)))
    ((1, 0), ((3, 6), (0, 791)))
    ...

This function returns an iterator that yields a pair of values. The second is
a window tuple that can be used in calls to read_band or write_band. The first
is the pair of row and column indexes of this block within all blocks of the
dataset.

