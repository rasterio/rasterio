Frequently Asked Questions
==========================

Where is "ERROR 4: Unable to open EPSG support file gcs.csv" coming from and what does it mean?
-----------------------------------------------------------------------------------------------

The full message is "ERROR 4: Unable to open EPSG support file gcs.csv.  Try
setting the GDAL_DATA environment variable to point to the directory containing
EPSG csv files." The GDAL/OGR library prints this text to your process's stdout
stream when it can not find the gcs.csv data file it needs to interpret spatial
reference system information stored with a dataset. If you've never seen this
before, you can summon this message by setting GDAL_DATA to a bogus value in
your shell and running a command like ogrinfo:

.. code-block:: console

    $ GDAL_DATA="/path/to/nowhere" ogrinfo example.shp -so example
    INFO: Open of 'example.shp'
          using driver 'ESRI Shapefile' successful.

    Layer name: example
    Geometry: Polygon
    Feature Count: 67
    Extent: (-113.564247, 37.068981) - (-104.970871, 41.996277)
    ERROR 4: Unable to open EPSG support file gcs.csv.  Try setting the GDAL_DATA environment variable to point to the directory containing EPSG csv files.

If you're using GDAL software installed by a package management system like apt
or yum, or Homebrew, or if you've built and installed it using ``configure;
make; make install``, you don't need to set the GDAL_DATA environment variable.
That software has the right directory path built in. If you see this error,
it's likely a sign that GDAL_DATA is set to a bogus value. Unset GDAL_DATA if
it exists and see if that eliminates the error condition and the message.

If you're installing GDAL into a Conda environment or into a Python virtual
environment (remember that the Rasterio wheels on the Python Package Index
include a GDAL library and its data files) the situation is different. The
proper data directory path is not built in and GDAL_DATA must be set.

Rasterio 1.0.18, whether from PyPI or Conda, will set the GDAL_DATA environment
variable to the correct location when it is imported, but only if it has not
already been set. Previous versions of Rasterio tried to avoid patching the
environment of the process, but there's really no better option.

Get the latest version of Rasterio, 1.0.18, and use it without setting
GDAL_DATA. You shouldn't experience the error condition or the message about
it.

Why can't rasterio find proj.db?
--------------------------------

If you see ``rasterio.errors.CRSError: The EPSG code is unknown. PROJ: proj_create_from_database: Cannot find proj.db`` it is because the PROJ library (one of rasterio's dependencies) cannot find its database of projections and coordinate systems. In some installations the ``PROJ_LIB`` `environment variable must be set <https://proj.org/usage/environmentvars.html#envvar-PROJ_LIB>`__ for PROJ to work properly.

.. important:: activate your conda environments.
   The PROJ conda package will set ``PROJ_LIB`` to the proper value if you activate your conda environment. If you don't activate your conda enviornment, you are likely to see the exception shown above.
