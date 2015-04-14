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
      --version      Show the version and exit.
      --help         Show this message and exit.

    Commands:
      bounds     Write bounding boxes to stdout as GeoJSON.
      env        Print information about the rio environment.
      extract    Extract raster using features.
      info       Print information about a data file.
      insp       Open a data file and start an interpreter.
      merge      Merge a stack of raster datasets.
      rasterize  Rasterize features.
      sample     Sample a dataset.
      shapes     Write the shapes of features.
      stack      Stack a number of bands into a multiband dataset.

It is developed using `Click <http://click.pocoo.org/3/>`__.

Commands are shown below. See ``--help`` of individual commands for more
details.

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

calc
----

The calc command reads files as arrays, evaluates lisp-like expressions in
their context, and writes the result as a new file. Members of the numpy
module and arithmetic and logical operators are available builtin functions
and operators. It is intended for simple calculations; any calculations
requiring multiple steps is better done in Python using the Rasterio and Numpy
APIs.

Input files may have different numbers of bands but should have the same
number of rows and columns. The output file will have the same number of rows
and columns as the inputs and one band per element of the expression result.
An expression involving arithmetic operations on N-D arrays will produce a
N-D array and result in an N-band output file.

The following produces a 3-band GeoTIFF with all values scaled by 0.95 and
incremented by 2. In the expression, ``(read 1)`` evaluates to the first
input dataset (3 bands) as a 3-D array.

.. code-block:: console

    $ rio calc "(+ 2 (* 0.95 (read 1)))" tests/data/RGB.byte.tif /tmp/out.tif

The following produces a 3-band GeoTIFF in which the first band is copied from
the first band of the input and the next two bands are scaled (down) by the
ratio of the first band's mean to their own means. The ``--name`` option is
used to bind datasets to a name within the expression. ``(take a 1)`` gets the
first band of the dataset named ``a`` as a 2-D array and ``(asarray ...)``
collects a sequence of 2-D arrays into a 3-D array for output.

.. code-block:: console

    $ rio calc "(asarray (take a 1) (* (take a 2) (/ (mean (take a 1)) (mean (take a 2)))) (* (take a 3) (/ (mean (take a 1)) (mean (take a 3)))))" \
    > --name a=tests/data/RGB.byte.tif /tmp/out.rgb.tif

The command above is also an example of a calculation that is far beyond the
design of the calc command and something that could be done much more
efficiently in Python.

Please see `calc.rst <calc.rst>`__ for more details.


extract
-------

New in 0.21

The extract command extracts pixels from all bands of a raster using features
(masking out all areas not covered by features) and optionally crops the output
raster to the extent of the features.  Features are assumed to be in the same
coordinate reference system as the input raster.

A common use case is extracting raster data by political or other boundaries.

.. code-block:: console

    $ rio extract input.tif output.tif < input.geojson

GeoJSON features may be provided using stdin or specified directly as first
argument.

.. code-block:: console

    $ rio rasterize input.geojson input.tif output.tif --crop

The feature mask can be inverted to mask out pixels covered by features and
extract pixels not covered by features.

.. code-block:: console

    $ rio rasterize input.geojson input.tif output.tif --invert


info
----

Rio's info command prints structured information about a dataset.

.. code-block:: console

    $ rio info tests/data/RGB.byte.tif --indent 2
    {
      "count": 3,
      "crs": "EPSG:32618",
      "dtype": "uint8",
      "driver": "GTiff",
      "bounds": [
        101985.0,
        2611485.0,
        339315.0,
        2826915.0
      ],
      "lnglat": [
        -77.75790625255473,
        24.561583285327067
      ],
      "height": 718,
      "width": 791,
      "shape": [
        718,
        791
      ],
      "res": [
        300.0379266750948,
        300.041782729805
      ],
      "nodata": 0.0
    }

More information, such as band statistics, can be had using the `--verbose`
option.

.. code-block:: console

    $ rio info tests/data/RGB.byte.tif --indent 2
    {
      "count": 3,
      "crs": "EPSG:32618",
      "stats": [
        {
          "max": 255.0,
          "mean": 44.434478650699106,
          "min": 1.0
        },
        {
          "max": 255.0,
          "mean": 66.02203484105824,
          "min": 1.0
        },
        {
          "max": 255.0,
          "mean": 71.39316199120559,
          "min": 1.0
        }
      ],
      "dtype": "uint8",
      "driver": "GTiff",
      "bounds": [
        101985.0,
        2611485.0,
        339315.0,
        2826915.0
      ],
      "lnglat": [
        -77.75790625255473,
        24.561583285327067
      ],
      "height": 718,
      "width": 791,
      "shape": [
        718,
        791
      ],
      "res": [
        300.0379266750948,
        300.041782729805
      ],
      "nodata": 0.0
    }

insp
----

The insp command opens a dataset and an interpreter.

.. code-block:: console

    $ rio insp tests/data/RGB.byte.tif
    Rasterio 0.18 Interactive Inspector (Python 2.7.9)
    Type "src.meta", "src.read_band(1)", or "help(src)" for more information.
    >>> print src.name
    tests/data/RGB.byte.tif
    >>> print src.bounds
    BoundingBox(left=101985.0, bottom=2611485.0, right=339315.0, top=2826915.0)

merge
-----

The merge command can be used to flatten a stack of identically structured
datasets.

.. code-block:: console

    $ rio merge rasterio/tests/data/R*.tif merged.tif

rasterize
---------

New in 0.18.

The rasterize command rasterizes GeoJSON features into a new or existing
raster.

.. code-block:: console

    $ rio rasterize test.tif --res 0.0167 < input.geojson

The resulting file will have an upper left coordinate determined by the bounds
of the GeoJSON (in EPSG:4326, which is the default), with a
pixel size of approximately 30 arc seconds.  Pixels whose center is within the
polygon or that are selected by brezenhams line algorithm will be burned in
with a default value of 1.

It is possible to rasterize into an existing raster and use an alternative
default value:

.. code-block:: console

    $ rio rasterize existing.tif --default_value 10 < input.geojson

It is also possible to rasterize using a template raster, which will be used
to determine the transform, dimensions, and coordinate reference system of the
output raster:

.. code-block:: console

    $ rio rasterize test.tif --like tests/data/shade.tif < input.geojson

GeoJSON features may be provided using stdin or specified directly as first
argument, and dimensions may be provided in place of pixel resolution:

.. code-block:: console

    $ rio rasterize input.geojson test.tif --dimensions 1024 1024

Other options are available, see:

.. code-block:: console

    $ rio rasterize --help

sample
------

New in 0.18.

The sample command reads ``x, y`` positions from stdin and writes the dataset
values at that position to stdout.

.. code-block:: console

    $ cat << EOF | rio sample tests/data/RGB.byte.tif
    > [220649.99999832606, 2719199.999999095]
    > EOF
    [18, 25, 14]

The output of the transform command (see below) makes good input for sample.

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

- ``--bidx N`` takes the Nth band from the input (first band is 1).
- ``--bidx M,N,O`` takes bands M, N, and O.
- ``--bidx M..O`` takes bands M-O, inclusive.
- ``--bidx ..N`` takes all bands up to and including N.
- ``--bidx N..`` takes all bands from N to the end.

Examples using the Rasterio testing dataset that produce a copy of it.

.. code-block:: console

    $ rio stack RGB.byte.tif stacked.tif
    $ rio stack RGB.byte.tif --bidx 1,2,3 stacked.tif
    $ rio stack RGB.byte.tif --bidx 1..3 stacked.tif
    $ rio stack RGB.byte.tif --bidx ..2 RGB.byte.tif --bidx 3.. stacked.tif

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
