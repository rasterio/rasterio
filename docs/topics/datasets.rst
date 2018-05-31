Advanced Datasets
=================

The analogy of Python file objects influences the design of Rasterio dataset
objects. Datasets of a few different kinds exist and the canonical way to
obtain one is to call ``rasterio.open`` with a path-like object or URI-like
identifier, a mode (such as "r" or "w"), and other keyword arguments.

Dataset Identifiers
-------------------

Datasets in a computer's filesystem are identified by paths, "file" URLs,
or instances of ``pathlib.Path``. The following are equivalent.

* ``'/path/to/file.tif'``
* ``'file:///path/to/file.tif'``
* ``pathlib.Path('/path/to/file.tif')``

Datasets within a local zip file are identified using the "zip" scheme from
`Apache Commons VFS <https://commons.apache.org/proper/commons-vfs/filesystems.html#Zip_Jar_and_Tar>`__.

* ``'zip:///path/to/file.zip!/folder/file.tif'``
* ``'zip+file:///path/to/file.zip!/folder/file.tif'``

Note that ``!`` is the separator between the path of the archive file and the
path within the archive file. Also note that his kind of identifier can't be expressed using
pathlib.

Similarly, variables of a netCDF dataset can be accessed using "netcdf" scheme
identifiers.

``'netcdf:/path/to/file.nc:variable'``

Datasets on the web are identifed by "http" or "https" URLs such as

* ``'https://example.com/file.tif'``
* ``'https://landsat-pds.s3.amazonaws.com/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF'``

Datasets within a zip file on the web
are identified using a "zip+https" scheme and paths separated by ``!`` as above.
For example:

``'zip+https://example.com/file.tif&p=x&q=y!/folder/file.tif'``

Datasets on AWS S3 may be identified using "s3" scheme identifiers.

``'s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF'``

Resources in other cloud storage systems will be similarly supported.
