Writing Datasets
=================

.. todo::

    * supported drivers
    * appending to existing data
    * context manager
    * write 3d vs write 2d
    * document issues with writing compressed files (per #77)
    * discuss and refer to topics
        * creation options
        * transforms
        * dtypes
        * block windows

Opening a file in writing mode is a little more complicated than opening
a text file in Python. The dimensions of the raster dataset, the 
data types, and the specific format must be specified.

Here's an example of basic rasterio functionality. 
An array is written to a new single band TIFF.

.. code-block:: python

    # Register GDAL format drivers and configuration options with a
    # context manager.
    with rasterio.Env():

        # Write the product as a raster band to a new 8-bit file. For
        # the new file's profile, we start with the meta attributes of
        # the source file, but then change the band count to 1, set the
        # dtype to uint8, and specify LZW compression.
        profile = src.profile
        profile.update(
            dtype=rasterio.uint8,
            count=1,
            compress='lzw')

        with rasterio.open('example-total.tif', 'w', **profile) as dst:
            dst.write(array.astype(rasterio.uint8), 1)

    # At the end of the ``with rasterio.Env()`` block, context
    # manager exits and all drivers are de-registered.

Writing data mostly works as with a Python file. There are a few format-
specific differences.
