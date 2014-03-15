Options
=======

GDAL's format drivers have many [configuration
options](https://trac.osgeo.org/gdal/wiki/ConfigOptions) The way to set options
for rasterio is via ``rasterio.drivers()``. Options set on entering are deleted
on exit.

.. code-block:: python

    import rasterio

    with rasterio.drivers(GDAL_TIFF_INTERNAL_MASK=True):
        # GeoTIFFs written here will have internal masks, not the
        # .msk sidecars.
        ...

    # Option is gone and the default (False) returns.

Use native Python forms (``True`` and ``False``) for boolean options. Rasterio
will convert them GDAL's internal forms.

