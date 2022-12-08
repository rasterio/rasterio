Virtual Files
=============

.. todo::

    Support for URIs describing zip, s3, https resources.
    Relationship to GDAL vsicurl, vsis3 et al.

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

S3 URIs and custom S3 Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, rasterio open with an AWS Session object all URIs that begin with
``s3://`` or containing ``amazonaws.com`` (except for Pre-signed URLs identified 
by the ``X-Amz-Signature`` query parameter).

It is possible to set addditional domains suffixes to be considered as S3 URIs by
setting the ``RIO_AWS_S3_DOMAINS`` environment variable with comma-separated domain names.
For instance ``s3.acme.com,s3.test.com`` will make rasterio consider
all URIs with these domain name suffixes as S3 URIs (e.g. ``"https://s3.acme.com/bucket/key"``
or ``"https://bucket.s3.test.com/key"``).
In this case, it is probably necessary to set as well the ``AWS_S3_ENDPOINT_URL`` environment
variable to the alternative endpoint for S3 service.
See `GDAL's documentation<https://gdal.org/user/virtual_file_systems.html#vsis3-aws-s3-files>` 
of the ``AWS_S3_ENDPOINT`` configuration option for more details.


.. note:: AWS pricing concerns
   While this feature can reduce latency by reading fewer bytes from S3
   compared to downloading the entire TIFF and opening locally, it does
   make at least 3 GET requests to fetch a TIFF's `profile` as shown above
   and likely many more to fetch all the imagery from the TIFF. Consult the
   AWS S3 pricing guidelines before deciding if `aws.Session` is for you.
