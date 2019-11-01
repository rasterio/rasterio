Options
=======

GDAL's format drivers have many `configuration options`_.
These options come in two flavors:

    * **Configuration options** are used to alter the default behavior of GDAL
      and OGR and are generally treated as global environment variables by GDAL. These
      are set through a :class:`rasterio.Env()` context block in Python.

    * **Creation options** are passed into the driver at dataset creation time as
      keyword arguments to ``rasterio.open(mode='w')``.

Configuration Options
---------------------

GDAL options are typically set as environment variables. While
environment variables will influence the behavior of ``rasterio``, we
highly recommended avoiding them in favor of defining behavior programatically.

The preferred way to set options for rasterio is via :class:`rasterio.Env()`.
Options set on entering the context are deleted on exit.

.. code-block:: python

    import rasterio

    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        # GeoTIFFs written here will have internal masks, not the
        # .msk sidecars.
        # ...

    # Option is gone and the default (False) returns.

Use native Python forms (``True`` and ``False``) for boolean options. Rasterio
will convert them GDAL's internal forms.

See the `configuration options`_ page for a complete list of available options.

Creation options
----------------

Each format has it's own set of driver-specific creation options that can be used to
fine tune the output rasters. For details on a particular driver, see the `formats list`_.

For the purposes of this document, we will focus on the `GeoTIFF creation options`_.
Some of the common GeoTIFF creation options include:

  * ``TILED``, ``BLOCKXSIZE``, and ``BLOCKYSIZE`` to define the internal tiling
  * ``COMPRESS`` to define the compression method
  * ``PHOTOMETRIC`` to define the band's color interpretation

To specify these creation options in python code, you pass them as keyword arguments
to the :func:`rasterio.open()` command in write mode.

.. code-block:: python

    with rasterio.open("output.tif", 'w', **src.meta, compress="JPEG",
                       tiled=True, blockxsize=256, blockysize=256,
                       photometric="YCBCR") as dataset:
        # Write data to the dataset.
        
.. note:: The GeoTIFF format requires that *blockxsize* and *blockysize* be multiples of 16.

On the command line, ``rio`` commands will accept multiple ``--co`` options.

.. code-block:: bash

    $ rio copy source.tif dest.tif --co tiled=true

These keyword arguments may be lowercase or uppercase, as you prefer.

.. attention:: Some options may at a glance appear to be boolean, but are not. The GeoTIFF format's BIGTIFF option is one of these. The value must be YES, NO, IF_NEEDED, or IF_SAFER.

.. note:: Some *configuration* options also have an effect on driver behavior at creation time.

.. _configuration options: https://trac.osgeo.org/gdal/wiki/ConfigOptions
.. _formats list: http://gdal.org/formats_list.html
.. _GeoTIFF creation options: http://gdal.org/frmt_gtiff.html
