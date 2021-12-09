============
Design Notes
============

Rasterio's design can be deduced from its code, but we can make it even more
comprehensible by writing about it in simple language. That's what this
document is about: describing the abstractions and design of the software to
project developers.

Interfaces
==========

Rasterio has interfaces that are not yet described using abstract base classes
or other formal interface system. The following subsections describe them
briefly.

DataAccessor
------------

This interface is involved with opening a dataset for access and is implemented
by the DatasetReader and DatasetWriter classes. Their constructors take a str
or os.PathLike object and, internally, attempt to adapt it to a
rasterio.path.Path object.

A DataAccessor is in some ways analogous to a Python I/O stream. It has an
access mode: "r", "r+", "w", or "w+". It can be in open or closed state. It is
a context manager. It has methods that read or write unlabeled arrays of raster
pixels to or from a dataset or optional windows (think slices) of a dataset. A
DataAccessor has more attributes than a Python I/O steam. There's no "encoding"
but there is a "crs" describing the coordinate reference system for the pixels
and a "transform", "gcps", or "rcps" attribute describing how the array indices
map to coordinates in that system.

Raster bands are not one of rasterio's abstractions. We don't read data from
the band of a dataset. We read multi-dimensional data from a dataset via a
DataAccessor.

Array
-----

A DataAccessor trades in not-sparse (dense) unlabeled Numpy arrays with a
minimum dimension of 2: row and column, or line and pixel. In the case of
multichannel/multiband datasets, like RGB imagery, there can also be a third
dimension corresponding to the channel or band. For these, the dimensions would
be: band, row, and column, in that order.

Elements of these arrays generally represent values integrated over an area.
Gridded point data can be handled, but it is not the default as it is with,
for example, xarray.

rasterio.path.Path
------------------

GDAL's GDALOpenEx takes an array of utf-8 encoded bytes as its primary
argument. These bytes may contain a filename, a URL, an RDBMS connection
string, XML, or JSON. Almost any kind of dataset address, really. GDAL puts no
constraint on the content at all. A future format driver might use an array of
emoji to address data and GDAL would be fine with that.

A rasterio.path.Path object contains a GDAL dataset address and has an as_vsi()
method, the result of which can be UTF-8 encoded and given to GDALOpenEx.

This interface isn't meant for public consumption. We might make it private, to
the extent that anything can be private in Python.

DataPath
--------

By analogy to Python's pathlib.Path, a rasterio DataPath has an open() method
that returns a DataAccessor.

rasterio.io.MemoryFile and rasterio.io.FilePath implement the DataPath
interface.

Opening a dataset
=================

rasterio.open() accepts a variety of inputs and returns a DataAccessor.

If the input implements DataPath, open() delegates to the input object. If the
input can be adapted to DataPath, open() delegates to the adapter. If the
input is a str or os.PathLike, it is adapted to rasterio.path.Path and passed
to a DataAccessor constructor.

Data types
==========

Rasterio uses Numpy data types and translates these to GDAL types before
calling GDAL methods.

GDAL context
============

GDAL relies on global state in the form of format drivers, a connection pool,
an error stack, caches, and configuration for these and optional software
features. Rasterio presents this context as a Python object:
rasterio.env.local._env. The rasterio.env.Env context manager is rasterio's
abstraction for configuration of the context. Importing rasterio creates the
absolute minimum of GDAL global state. It is not until an instance of
rasterio.env.Env is created and its context is entered, whether explicitly or
implicitly (by calling rasterio.open), that format drivers are registered and
rasterio.env.local._env becomes not None.

Many methods of rasterio require GDAL's context to be fully initialized. To
make this easy to ensure, we can use decorators from the rasterio.env module.
See for example the exists function in rasterio/shutil.pyx.

Errors and exceptions
=====================

GDAL maintains an error stack and a registry of handlers that are called when
an error is pushed onto the stack. Rasterio registers a handler that routes
GDAL error messages to Python's logger. We don't enable registration of other
handlers. Instead, users and developers should work with Python's logger.
Additionally, we check the error stack after calling GDAL functions from Cython
extension code and raise a Python exception if the last error is of GDAL type
>= 3. Several functions in rasterio._err exist to help: exc_wrap_int,
>exc_wrap_pointer, etc.

GDAL raster band cache
======================

GDAL has a per-process in-memory LRU (least recently used) raster block cache.
A DataAccessor's read method results in cached blocks. Subsequent reads from
the same accessor may reuse those cached blocks. Calling a DataAccessor's write
method will update cached blocks. Cached blocks are written to the dataset's
storage when evicted from the cache or when the DataAccessor is closed,
flushing all the dataset's cached blocks.

Rasterio has no abstraction for this cache.
