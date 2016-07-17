============
Introduction
============

Background
----------

Before Rasterio, there was one way to access the many different kind of raster
data files used in the GIS field with Python: the Python bindings to GDAL.
These bindings provide almost no abstraction for GDAL's C API and Python
programs using them read and run like C programs.

Philosophy
----------

Rasterio has a different philosophy. It uses GDAL and the GDAL C API but is not
a "Python binding for GDAL."

Raster data has unique qualities but is not too special for common Python
abstractions. Rasterio prefers Python's built-in protocols and types or Numpy
protocols and types over concepts from GDAL's data model.

Rasterio helps keep input/output separate from other operations.
``rasterio.open()`` is the only library function that operates on filenames and
URIs. ``dataset.read()``, ``dataset.write()``, and their mask counterparts are
the methods that do I/O.

Rasterio methods and functions avoid hidden inputs and side-effects. GDAL's
C API uses global variables liberally, but Rasterio provides abstractions that
make them less dangerous.

Rasterio delegates calculation of raster data properties almost entirely to
Numpy and uses GDAL mainly for input/output. The mean, min, and max values of
a raster dataset, for example, are properties of a GDAL dataset object. They
are not properties of a Rasterio dataset, but are properties of the N-D array
returned by ``dataset.read()``. Thus Rasterio objects are more limited than
GDAL objects.
