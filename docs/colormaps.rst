Colormaps
=========

Writing colormaps
-----------------

Mappings from 8-bit (rasterio.uint8) pixel values to RGBA values can be attached
to bands using the ``write_colormap()`` method.

.. code-block:: python

    import rasterio

    with rasterio.drivers():

        with rasterio.open('tests/data/shade.tif') as src:
            shade = src.read_band(1)
            meta = src.meta

        with rasterio.open('/tmp/colormap.tif', 'w', **meta) as dst:
            dst.write_band(1, shade)
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

As shown above, the ``colormap()`` returns a dict holding the colormap for the 
given band index. For TIFF format files, the colormap will have 256 items, and
all but two of those would map to (0, 0, 0, 0) in the example above.

