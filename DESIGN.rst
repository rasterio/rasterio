============
Design Notes
============

Introduction
============

TODO.

Interfaces
==========

Rasterio has interfaces that are not yet described using abstract base classes
or other formal interface system.

DataAccessor
------------

This interface is involved with opening a dataset for access and is implemented
by the DatasetReader and DatasetWriter classes. Their constructors take a str
or os.PathLike object and, internally, attempt to adapt it to a
rasterio.path.Path object.

rasterio.path.Path
------------------

GDAL's GDALOpenEx takes an array of utf-8 encoded bytes as its primary
argument. These bytes may contain a filename, a URL, an RDBMS connection
string, XML, or JSON. Almost any kind of dataset address, really. GDAL puts no
constraint on the content at all. A future format driver might use an array of
emoji to address data and GDAL would be fine with that.

A rasterio.path.Path object contains a GDAL dataset address and has an as_vsi()
method, the result of which can be UTF-8 encoded and given to GDALOpenEx.

DataPath
--------

By analogy to Python's pathlib.Path, a rasterio DataPath has an open() method
that returns a DataAccessor.

rasterio.io.MemoryFile and rasterio.io.FilePath implement the DataPath
interface.

Opening a dataset
=================

rasterio.open() accepts a variety of inputs and returns a DataAccessor.

If the input implements DataPath, open() dispatches to the input object. If the
input can be adapted to DataPath, open() dispatches to the adapter. If the
input is a str or os.PathLike, it is adapted to rasterio.path.Path and passed
to a DataAccessor constructor.
