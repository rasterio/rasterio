Profiles and Writing Files
==========================

How to use profiles when opening files.

Like Python's built-in ``open()`` function, ``rasterio.open()`` has two primary
arguments: a path (or URL) and an optional mode (``'r'``, ``'w'``, ``'r+'``, or
``'w+'``). In addition there are a number of keyword arguments, several of
which are required when creating a new dataset:

- driver
- width, height
- count
- dtype
- crs
- transform

These same parameters surface in a dataset's ``profile`` property. Exploiting
the symmetry between a profile and dataset opening keyword arguments is
good Rasterio usage.

.. code-block:: python

   with rasterio.open('first.jp2') as src_dataset:

       # Get a copy of the source dataset's profile. Thus our
       # destination dataset will have the same dimensions,
       # number of bands, data type, and georeferencing as the
       # source dataset.
       kwds = src_dataset.profile

       # Change the format driver for the destination dataset to
       # 'GTiff', short for GeoTIFF.
       kwds['driver'] = 'GTiff'

       # Add GeoTIFF-specific keyword arguments.
       kwds['tiled'] = True
       kwds['blockxsize'] = 256
       kwds['blockysize'] = 256
       kwds['photometric'] = 'YCbCr'
       kwds['compress'] = 'JPEG'

       with rasterio.open('second.tif', 'w', **kwds) as dst_dataset:
           # Write data to the destination dataset.

The ``rasterio.profiles`` module contains an example of a named profile that
may be useful in applications:

.. code-block:: python
   
    class DefaultGTiffProfile(Profile):
        """Tiled, band-interleaved, LZW-compressed, 8-bit GTiff."""

        defaults = {
            'driver': 'GTiff',
            'interleave': 'band',
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256,
            'compress': 'lzw',
            'nodata': 0,
            'dtype': uint8
        }

It can be used to create new datasets. Note that it doesn't count bands and
that a ``count`` keyword argument needs to be passed when creating a profile.

.. code-block:: python

   from rasterio.profiles import DefaultGTiffProfile

   with rasterio.open(
           'output.tif', 'w', **DefaultGTiffProfile(count=3)) as dst_dataset:
       # Write data to the destination dataset.


