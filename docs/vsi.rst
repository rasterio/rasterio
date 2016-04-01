Virtual Files
*************

.. todo:: 

    Support for URIs describing zip, s3, etc resources. Relationship to GDAL
    vsicurl et al.

AWS S3
======

After you have configured your AWS credentials as explained in the `boto3 guide
<http://boto3.readthedocs.org/en/latest/guide/configuration.html>`__ you can
read metadata and imagery from S3 objects with little change to your code.
Add a `rasterio.aws.Session` as shown below.

.. code-block:: python

    >>> import pprint
    >>> import rasterio
    >>> from rasterio.aws import Session
    >>> with rasterio.drivers(), Session():
    ...     with rasterio.open('s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF') as src:
    ...         pprint.pprint(src.profile)
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
