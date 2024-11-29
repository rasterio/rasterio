Virtual Filesystems
===================

Rasterio uses GDAL's `virtual filesystem interface
<https://gdal.org/user/virtual_file_systems.html>`__ to access datasets on the
web, in cloud storage, in archive files, and in Python objects. Rasterio maps
familiar URI schemes to GDAL virtual filesystem handlers. For example, the
``https`` URI scheme maps to GDAL's ``/vsicurl/``. The ``file`` URI scheme maps
to GDAL's ordinary filesystem handler and is the default for dataset URIs that
have no other scheme.

To access a dataset in a local ZIP file like the one in Rasterio's test suite,
prepend ``zip`` to the URI of the local file and add the interior path to the
dataset after a ``!`` character. For example:

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

Similarly, datasets in ZIP files served on the web can be accessed by using
``zip+https``.

.. code-block:: python

    with rasterio.open("zip+https://github.com/rasterio/rasterio/files/13675561/files.zip!RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

Tar and gzip archives can be accessed in the same manner by prepending with
``tar`` or ``gz`` instead of ``zip``.

For compatibility with legacy systems and workflows or very niche use cases,
Rasterio can also use GDAL's VSI filenames.

.. code-block:: python

    with rasterio.open("/vsizip/vsicurl/https://github.com/rasterio/rasterio/files/13675561/files.zip/RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

The prefixes on which GDAL filesystem handlers are registered are considered by
Rasterio to be an implementation detail. You shouldn't need to think about them
when using Rasterio. Use familiar and standard URIs instead, like elsewhere on
the internet.

.. code-block:: python

    with rasterio.open("https://github.com/rasterio/rasterio/raw/main/tests/data/RGB.byte.tif") as src:
        print(src.shape)

    # Printed:
    # (718, 791)

AWS S3
------

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

Python file and filesystem openers
----------------------------------

Datasets stored in proprietary systems or addressable only through protocols
not directly supported by GDAL can be accessed using the ``opener`` keyword
argument of ``rasterio.open``. Here is an example of using ``fs_s3fs`` to
access the dataset in
``sentinel-s2-l2a-cogs/45/C/VQ/2022/11/S2B_45CVQ_20221102_0_L2A/B01.tif`` from
the ``sentinel-cogs`` AWS S3 bucket. Rasterio can access this without using the
``opener`` argument, but it makes a good usage example. Other custom openers
would work in the same way.

.. code-block:: python

    import rasterio
    from fs_s3fs import S3FS

    fs = S3FS(
        bucket_name="sentinel-cogs",
        dir_path="sentinel-s2-l2a-cogs/45/C/VQ/2022/11/S2B_45CVQ_20221102_0_L2A",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    with rasterio.open("B01.tif", opener=fs.open) as src:
        print(src.profile)


In this code AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are placeholders for the
appropriate credentials.

Read and write access is supported, with some limitations. Only one opener at
a time may be thus registered for a filename and access mode pair. Openers are
unregistered when the dataset is closed or its context is exited. The other
limitation is that auxiliary and sidecar files cannot be accessed and thus
formats depending on them cannot be used in this way.

To gain support for auxiliary "sidecar" files such as .aux.xml and .msk files
that may accompany GeoTIFFs, an fsspec-like filesystem object may be used as
the opener.

.. code-block:: python

    import rasterio
    from fsspec

    fs = fsspec.filesystem("s3", anon=True)

    with rasterio.open(
        "sentinel-cogs/sentinel-s2-l2a-cogs/45/C/VQ/2022/11/S2B_45CVQ_20221102_0_L2A/B01.tif",
        opener=fs
    ) as src:
        print(src.profile)

This kind of filesystem opener object must provide the following methods:
``isdir()``, ``isfile()``, ``ls()``, ``mtime()``, ``open()``, and ``size()``.

*New in version 1.4.0*
