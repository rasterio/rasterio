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
      bounds     Write bounding boxes to stdout as GeoJSON.
      info       Print information about a data file.
      insp       Open a data file and start an interpreter.
      merge      Merge a stack of raster datasets.
      shapes     Write the shapes of features.
      stack      Stack a number of bands into a multiband dataset.
      transform  Transform coordinates.

It is developed using the ``click`` package.


bounds
------

New in 0.10.

The bounds command writes the bounding boxes of raster datasets to GeoJSON for
use with, e.g., `geojsonio-cli <https://github.com/mapbox/geojsonio-cli>`__.

.. code-block:: console

    $ rio bounds tests/data/RGB.byte.tif --indent 2
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
            "title": "tests/data/RGB.byte.tif"
          },
          "type": "Feature"
        }
      ],
      "type": "FeatureCollection"
    }

Shoot the GeoJSON into a Leaflet map using geojsonio-cli by typing 
``rio bounds tests/data/RGB.byte.tif | geojsonio``.

info
----

Rio's info command intends to serve some of the same uses as gdalinfo.

.. code-block:: console

    $ rio info tests/data/RGB.byte.tif
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

insp
----

The insp command opens a dataset and an interpreter.

.. code-block:: console

    $ rio insp tests/data/RGB.byte.tif
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

merge
-----

The merge command can be used to flatten a stack of identically layed out
datasets.

.. code-block:: console

    $ rio merge rasterio/tests/data/R*.tif -o result.tif

shapes
------

New in 0.11.

The shapes command extracts and writes features of a specified dataset band out
as GeoJSON.

.. code-block:: console

    $ rio shapes tests/data/shade.tif --bidx 1 --precision 6 > shade.geojson

The resulting file, uploaded to Mapbox, looks like this: `sgillies.j1ho338j <https://a.tiles.mapbox.com/v4/sgillies.j1ho338j/page.html?access_token=pk.eyJ1Ijoic2dpbGxpZXMiLCJhIjoiWUE2VlZVcyJ9.OITHkb1GHNh9nvzIfUc9QQ#13/39.6079/-106.4822>`__.

Using the ``--mask`` option you can write out the shapes of a dataset's valid
data region.

.. code-block:: console

    $ rio shapes --mask --precision 6 tests/data/RGB.byte.tif | geojsonio

See http://bl.ocks.org/anonymous/raw/ef244954b719dba97926/.

stack
-----

New in 0.15.

The rio-stack command stack a number of bands from one or more input files into
a multiband dataset. Input datasets must be of a kind: same data type,
dimensions, etc. The output is cloned from the first input. By default,
rio-stack will take all bands from each input and write them in same order to
the output. Optionally, bands for each input may be specified using a simple
syntax:

- --bidx N takes the Nth band from the input (first band is 1).
- --bidx M,N,0 takes bands M, N, and O.
- --bidx M..O takes bands M-O, inclusive.
- --bidx ..N takes all bands up to and including N.
- --bidx N.. takes all bands from N to the end.

Examples using the Rasterio testing dataset that produce a copy of it.

.. code-block:: console

    $ rio stack RGB.byte.tif -o stacked.tif
    $ rio stack RGB.byte.tif --bidx 1,2,3 -o stacked.tif
    $ rio stack RGB.byte.tif --bidx 1..3 -o stacked.tif
    $ rio stack RGB.byte.tif --bidx ..2 RGB.byte.tif --bidx 3.. -o stacked.tif

transform
---------

New in 0.10.

The transform command reads a JSON array of coordinates, interleaved, and
writes another array of transformed coordinates to stdout.

To transform a longitude, latitude point (EPSG:4326 is the default) to 
another coordinate system with 2 decimal places of output precision, do the
following.

.. code-block:: console

    $ echo "[-78.0, 23.0]" | rio transform - --dst_crs EPSG:32618 --precision 2
    [192457.13, 2546667.68]

To transform a longitude, latitude bounding box to the coordinate system of
a raster dataset, do the following.

.. code-block:: console

    $ echo "[-78.0, 23.0, -76.0, 25.0]" | rio transform - --dst_crs tests/data/RGB.byte.tif --precision 2
    [192457.13, 2546667.68, 399086.97, 2765319.94]

Suggestions for other commands are welcome!
