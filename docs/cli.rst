Command Line Interface
======================

Rasterio's new command line interface is a program named "rio".

.. code-block:: console

    $ rio
    Usage: rio [OPTIONS] COMMAND [ARGS]...

      Rasterio command line interface.

    Options:
      -v, --verbose  Increase verbosity.
      -q, --quiet    Decrease verbosity.
      --help         Show this message and exit.

    Commands:
      bounds  Write bounding boxes to stdout as GeoJSON.
      info    Print information about a data file.
      insp    Open a data file and start an interpreter.

It is developed using the ``click`` package.

Rio's info command intends to serve some of the same uses as gdalinfo.

.. code-block:: console

    $ rio info rasterio/tests/data/RGB.byte.tif
    { 'affine': Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0),
      'count': 3,
      'crs': { 'init': u'epsg:32618'},
      'driver': u'GTiff',
      'dtype': <type 'numpy.uint8'>,
      'height': 718,
      'nodata': 0.0,
      'transform': ( 101985.0,
                     300.0379266750948,
                     0.0,
                     2826915.0,
                     0.0,
                     -300.041782729805),
      'width': 791}

The insp command opens a dataset and an interpreter.

.. code-block:: console

    $ rio insp rasterio/tests/data/RGB.byte.tif
    Rasterio 0.9 Interactive Inspector (Python 2.7.5)
    Type "src.meta", "src.read_band(1)", or "help(src)" for more information.
    >>> import pprint
    >>> pprint.pprint(src.meta)
    {'affine': Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0),
     'count': 3,
     'crs': {'init': u'epsg:32618'},
     'driver': u'GTiff',
     'dtype': <type 'numpy.uint8'>,
     'height': 718,
     'nodata': 0.0,
     'transform': (101985.0,
                   300.0379266750948,
                   0.0,
                   2826915.0,
                   0.0,
                   -300.041782729805),
     'width': 791}

The bounds command writes the bounding boxes of raster datasets to GeoJSON for
use with, e.g., `geojsonio-cli <https://github.com/mapbox/geojsonio-cli>`__.

.. code-block:: console

    $ rio bounds rasterio/tests/data/RGB.byte.tif --indent 2
    {
      "features": [
        {
          "geometry": {
            "coordinates": [
              [
                [
                  -78.898133,
                  23.564991
                ],
                [
                  -76.599438,
                  23.564991
                ],
                [
                  -76.599438,
                  25.550874
                ],
                [
                  -78.898133,
                  25.550874
                ],
                [
                  -78.898133,
                  23.564991
                ]
              ]
            ],
            "type": "Polygon"
          },
          "properties": {
            "id": "0",
            "title": "rasterio/tests/data/RGB.byte.tif"
          },
          "type": "Feature"
        }
      ],
      "type": "FeatureCollection"
    }

Shoot the GeoJSON into a Leaflet map using geojsonio-cli by typing 
``rio bounds rasterio/tests/data/RGB.byte.tif | geojsonio``.

Suggestions for other commands are welcome!

