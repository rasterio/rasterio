Virtual Files
*************

.. todo::

    Support for URIs describing zip, s3, etc resources. Relationship to GDAL
    vsicurl et al.

AWS S3
======

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
    # {'affine': Affine(30.0, 0.0, 381885.0,
    #        0.0, -30.0, 2512815.0),
    #  'blockxsize': 512,
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
    #  'transform': (381885.0, 30.0, 0.0, 2512815.0, 0.0, -30.0),
    #  'width': 7621}

.. note:: AWS pricing concerns
   While this feature can reduce latency by reading fewer bytes from S3
   compared to downloading the entire TIFF and opening locally, it does
   make at least 3 GET requests to fetch a TIFF's `profile` as shown above
   and likely many more to fetch all the imagery from the TIFF. Consult the
   AWS S3 pricing guidelines before deciding if `aws.Session` is for you.
