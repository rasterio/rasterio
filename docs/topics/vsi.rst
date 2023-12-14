Virtual Filesystems
===================

Rasterio uses GDAL's `virtual filesystem interface <https://gdal.org/user/virtual_file_systems.html>`__ to access datasets
on the web, in cloud storage, in archive files, and in Python objects. Rasterio maps familiar URI schemes to GDAL virtual filesystem handlers. For example, the ``https`` URI scheme maps to GDAL's ``/vsicurl/``. The ``file`` URI scheme maps to GDAL's ordinary filesystem handler and is the default for dataset URIs that have no other scheme.

To access a dataset in a local ZIP file like the one in Rasterio's test suite, preprend ``zip`` to the URI of the local file and add the interior path to the dataset after a ``!`` character. For example:

.. code-block:: python

    with rasterio.open("zip+file://tests/data/files.zip!RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

Or use ``zip`` as shorthand for ``zip+file``.

.. code-block:: python

    with rasterio.open("zip://tests/data/files.zip!RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

Similarly, datasets in ZIP files served on the web can be accessed by using ``zip+https``.

.. code-block:: python

    with rasterio.open("zip+https://github.com/rasterio/rasterio/files/13675561/files.zip!RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

Tar and gzip archives can be accessed in the same manner by prepending with ``tar`` or ``gz`` instead of ``zip``.

For compatibility with legacy systems and workflows or very niche use cases, Rasterio can also use GDAL's VSI filenames.

.. code-block:: python

    with rasterio.open("/vsizip/vsicurl/https://github.com/rasterio/rasterio/files/13675561/files.zip/RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

The prefixes on which GDAL filesystem handlers are registered are considered by Rasterio to be an implementation detail. You shouldn't need to think about them when using Rasterio. Use familiar and standard URIs instead, like elsewhere on the internet.

.. code-block:: python

    with rasterio.open("https://github.com/rasterio/rasterio/raw/main/tests/data/RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

AWS S3
------

.. note::
    Requires GDAL 2.1.0

This is an extra feature that must be installed by executing

.. code-block:: console

    pip install rasterio[s3]

After you have configured your AWS credentials as explained in the `boto3 guide
<http://boto3.readthedocs.org/en/latest/guide/configuration.html>`__ you can
read metadata and imagery from TIFFs stored as S3 objects with no change to
your code.

.. code-block:: python

    with rasterio.open("s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF") as src:
        print(src.profile)

    # Printed:
    # {'blockxsize': 512,
    #  'blockysize': 512,
    #  'compress': 'deflate',
    #  'count': 1,
    #  'crs': {'init': u'epsg:32645'},
    #  'driver': u'GTiff',
    #  'dtype': 'uint16',
    #  'height': 7791,
    #  'interleave': 'band',
    #  'nodata': None,
    #  'tiled': True,
    #  'transform': Affine(30.0, 0.0, 381885.0,
    #        0.0, -30.0, 2512815.0),
    #  'width': 7621}

.. note:: AWS pricing concerns
   While this feature can reduce latency by reading fewer bytes from S3
   compared to downloading the entire TIFF and opening locally, it does
   make at least 3 GET requests to fetch a TIFF's `profile` as shown above
   and likely many more to fetch all the imagery from the TIFF. Consult the
   AWS S3 pricing guidelines before deciding if `aws.Session` is for you.
