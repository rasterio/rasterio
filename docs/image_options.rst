Options
*******

GDAL's format drivers have many `configuration options`_.
These options come in two flavors:

    * General GDAL options
    * Driver-specific creation options 

General Options
-----------------

GDAL options are typically set as environment variables. While
environment variables will influence the behavior of ``rasterio``, we
highly recommended avoiding them in favor of defining behavior programatically.

The preferred way to set options for rasterio is via ``rasterio.Env()``.
Options set on entering the context are deleted on exit.

.. code-block:: python

    import rasterio

    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        # GeoTIFFs written here will have internal masks, not the
        # .msk sidecars.
        ...

    # Option is gone and the default (False) returns.

Use native Python forms (``True`` and ``False``) for boolean options. Rasterio
will convert them GDAL's internal forms.

See the `configuration options`_ page for a complete list of available options.


Creation options
-----------------

Each format has it's own set of driver-specific creation options that can be used to
fine tune the output rasters. For details on a particular driver, see the `formats list`_.

For the purposes of this document, we will focus on the `GeoTIFF creation options`_.
Some of the common GeoTIFF creation options include:

  * ``TILED``, ``BLOCKXSIZE``, and ``BLOCKYSIZE`` to define the internal tiling
  * ``COMPRESS`` to define the compression method
  * ``PHOTOMETRIC`` to define the band's color interpretation

To specify these creation options in python code, you pass them as keyword arguments
to the ``rasterio.open()`` command in write mode::

    with rasterio.open("output.tif", 'w', **src.meta, compress="JPEG",
                       tiled=True, blockxsize=256, blockysize=256,
                       photometric="YCBCR") as dest:
        ...

Or at the command line, ``rio`` commands will accept multiple ``--co`` options::

    rio copy source.tif dest.tif --co tiled=true

                       

.. _configuration options: https://trac.osgeo.org/gdal/wiki/ConfigOptions
.. _formats list: http://gdal.org/formats_list.html
.. _GeoTIFF creation options: http://gdal.org/frmt_gtiff.html
