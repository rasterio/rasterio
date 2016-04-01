Virtual Files
*************

.. todo:: 

    Support for URIs describing zip, s3, etc resources. Relationship to GDAL
    vsicurl et al.

AWS S3
======

After you have configured your AWS credentials as explained in the `boto3 guide
<http://boto3.readthedocs.org/en/latest/guide/configuration.html>`__ you can
read metadata and imagery from TIFFs stored as S3 objects with little change to
your code.  Add a `rasterio.aws.Session` as shown below.

.. code-block:: pycon

    >>> import pprint
    >>> from rasterio.aws import Session
    >>> session = Session()
    >>> with session.open('s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF') as src:
    ...     pprint.pprint(src.profile)
    ...
    {'affine': Affine(30.0, 0.0, 381885.0,
           0.0, -30.0, 2512815.0),
     'blockxsize': 512,
     'blockysize': 512,
     'compress': 'deflate',
     'count': 1,
     'crs': {'init': u'epsg:32645'},
     'driver': u'GTiff',
     'dtype': 'uint16',
     'height': 7791,
     'interleave': 'band',
     'nodata': None,
     'tiled': True,
     'transform': (381885.0, 30.0, 0.0, 2512815.0, 0.0, -30.0),
     'width': 7621}

If you provide no arguments when creating a session, your environment will be
checked for credentials. Access keys may be explicitly provided when creating
a session.

.. code-block:: python

    session = Session(aws_access_key_id='KEY',
                      aws_secret_access_key='SECRET',
                      aws_session_token='TOKEN')

.. note:: AWS pricing concerns
   While this feature can reduce latency by reading fewer bytes from S3
   compared to downloading the entire TIFF and opening locally, it does
   make at least 3 GET requests to fetch a TIFF's `profile` as shown above
   and likely many more to fetch all the imagery from the TIFF. Consult the
   AWS S3 pricing guidelines before deciding if `aws.Session` is for you.
