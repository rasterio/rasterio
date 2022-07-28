Color
=====

Color interpretation
--------------------

Color interpretation of raster bands can be read from the dataset

.. code-block:: python

    >>> import rasterio
    >>> src = rasterio.open("tests/data/RGB.byte.tif")
    >>> src.colorinterp[0]
    <ColorInterp.red: 3>

GDAL builds the color interpretation based on the driver and creation options.
With the ``GTiff`` driver, rasters with exactly 3 bands of uint8 type will be RGB,
4 bands of uint8 will be RGBA by default.

Color interpretation can be set when creating a new datasource with the
``photometric`` creation option:

.. code:: python

    >>> profile = src.profile
    >>> profile['photometric'] = "RGB"
    >>> with rasterio.open("/tmp/rgb.tif", 'w', **profile) as dst:
    ...     dst.write(src.read())

or via the :attr:`~.DatasetWriter.colorinterp` property when a datasource is opened in
update mode:

.. code:: python

    >>> from rasterio.enums import ColorInterp
    >>> with rasterio.open('/tmp/rgb.tif', 'r+', **profile) as src:
    ...     src.colorinterp = [
    ...         ColorInterp.red, ColorInterp.green, ColorInterp.blue]

And the resulting raster will be interpretted as RGB.

.. code:: python

    >>> with rasterio.open("/tmp/rgb.tif") as src2:
    ...     src2.colorinterp[1]
    <ColorInterp.green: 4>

Writing colormaps
-----------------

Mappings from 8-bit (rasterio.uint8) pixel values to RGBA values can be attached
to bands using the :meth:`~.DatasetWriter.write_colormap` method.

.. code-block:: python

    import rasterio

    with rasterio.Env():

        with rasterio.open('tests/data/shade.tif') as src:
            shade = src.read(1)
            meta = src.meta

        with rasterio.open('/tmp/colormap.tif', 'w', **meta) as dst:
            dst.write(shade, indexes=1)
            dst.write_colormap(
                1, {
                    0: (255, 0, 0, 255), 
                    255: (0, 0, 255, 255) })
            cmap = dst.colormap(1)
            # True
            assert cmap[0] == (255, 0, 0, 255)
            # True
            assert cmap[255] == (0, 0, 255, 255)

    subprocess.call(['open', '/tmp/colormap.tif'])

The program above (on OS X, another viewer is needed with a different OS)
yields the image below:

.. image:: http://farm8.staticflickr.com/7391/12443115173_80ecca89db_d.jpg
   :width: 500
   :height: 500

Reading colormaps
-----------------

As shown above, the :meth:`~.DatasetReader.colormap` returns a dict holding the colormap for the 
given band index. For TIFF format files, the colormap will have 256 items, and
all but two of those would map to (0, 0, 0, 0) in the example above.
