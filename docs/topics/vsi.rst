Virtual Filesystems
===================

.. todo::

    Support for URIs describing zip, s3, https resources.
    Relationship to GDAL vsicurl, vsis3 et al.

Rasterio relies on GDAL's virtual filesystem interface to access datasets
on the web, in cloud storage, in archive files, and in Python objects.

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

    with rasterio.open('s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF') as src:
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

Python file openers
-------------------

Datasets stored in proprietary systems or addressable only through protocols
not directly supported by GDAL can be accessed using the ``opener`` keyword
argument of ``rasterio.open``. Here is an example of using ``fs_s3fs`` to
access the dataset in
``sentinel-s2-l2a-cogs/45/C/VQ/2022/11/S2B_45CVQ_20221102_0_L2A/B01.tif`` from
the ``sentinel-cogs`` AWS S3 bucket. Rasterio can access this without using the
``opener`` argument, but it makes a good usage example. Other custom openers
would work in the same way.

.. code-block::

    import rasterio
    from fs_s3fs import S3FS

    fs = S3FS(
        bucket_name="sentinel-cogs",
        dir_path="sentinel-s2-l2a-cogs/45/C/VQ/2022/11/S2B_45CVQ_20221102_0_L2A",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    with rasterio.open("B01.tif", opener=fs.openbin) as src:
        print(src.profile)


Where AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are placeholders for the
appropriate credentials.
