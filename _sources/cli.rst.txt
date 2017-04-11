========================
Command Line Users Guide
========================

Rasterio's command line interface is a program named ``rio``.

``rio`` allows you to build workflows using shell commands, either
interactively at the command prompt or with a script. Most common
cases are covered by ``rio`` commands and it is often more convenient
to use a ready-made command as opposed to implementing similar functionality
as a python script.

``rio`` is developed using the `Click <http://click.pocoo.org/>`__  architecture.
Its plugin system allows external modules to share a common namespace and
handling of context variables.

.. code-block:: console

    $ rio --help
    Usage: rio [OPTIONS] COMMAND [ARGS]...

      Rasterio command line interface.

    Options:
      -v, --verbose  Increase verbosity.
      -q, --quiet    Decrease verbosity.
      --version      Show the version and exit.
      --help         Show this message and exit.

    Commands:
      bounds     Write bounding boxes to stdout as GeoJSON.
      calc       Raster data calculator.
      clip       Clip a raster to given bounds.
      convert    Copy and convert raster dataset.
      edit-info  Edit dataset metadata.
      env        Print information about the rio environment.
      info       Print information about a data file.
      insp       Open a data file and start an interpreter.
      mask       Mask in raster using features.
      merge      Merge a stack of raster datasets.
      overview   Construct overviews in an existing dataset.
      rasterize  Rasterize features.
      sample     Sample a dataset.
      shapes     Write shapes extracted from bands or masks.
      stack      Stack a number of bands into a multiband dataset.
      transform  Transform coordinates.
      warp       Warp a raster dataset.


Commands are shown below. See ``--help`` of individual commands for more
details.


creation options
----------------

For commands that create new datasets, format specific creation options may
also be passed using ``--co``. For example, to tile a new GeoTIFF output file,
add the following.

.. code-block:: console

    --co tiled=true --co blockxsize=256 --co blockysize=256

To compress it using the LZW method, add

.. code-block:: console

    --co compress=LZW


bounds
------

Added in 0.10.

The ``bounds`` command writes the bounding boxes of raster datasets to GeoJSON for
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

Added in 0.19

The ``calc`` command reads files as arrays, evaluates lisp-like expressions in
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

.. toctree::

    calc

clip
----

Added in 0.27

The ``clip`` command clips a raster using bounds input directly or from a
template raster.

.. code-block:: console

    $ rio clip input.tif output.tif --bounds xmin ymin xmax ymax
    $ rio clip input.tif output.tif --like template.tif

If using ``--bounds``, values must be in coordinate reference system of input.
If using ``--like``, bounds will automatically be transformed to match the
coordinate reference system of the input.

It can also be combined to read bounds of a feature dataset using Fiona:

.. code-block:: console

    $ rio clip input.tif output.tif --bounds $(fio info features.shp --bounds)



convert
-------

Added in 0.25

The ``convert`` command copies and converts raster datasets to other data types
and formats (similar to ``gdal_translate``).

Data values may be linearly scaled when copying by using the ``--scale-ratio``
and ``--scale-offset`` options. Destination raster values are calculated as

.. code-block:: python

    dst = scale_ratio * src + scale_offset

For example, to scale uint16 data with an actual range of 0-4095 to 0-255
as uint8:

.. code-block:: console

    $ rio convert in16.tif out8.tif --dtype uint8 --scale-ratio 0.0625

You can use `--rgb` as shorthand for `--co photometric=rgb`.


edit-info
---------

Added in 0.24

The ``edit-info`` command allows you edit a raster dataset's metadata, namely

- coordinate reference system
- affine transformation matrix
- nodata value
- tags

A TIFF created by spatially-unaware image processing software like Photoshop
or Imagemagick can be turned into a GeoTIFF by editing these metadata items.

For example, you can set or change a dataset's coordinate reference system to
Web Mercator (EPSG:3857),

.. code-block:: console

    $ rio edit-info --crs EPSG:3857 example.tif

set its `affine transformation matrix <https://github.com/mapbox/rasterio/blob/master/docs/georeferencing.rst#coordinate-transformation>`__,

.. code-block:: console

    $ rio edit-info --transform "[300.0, 0.0, 101985.0, 0.0, -300.0, 2826915.0]" example.tif

or set its nodata value to, e.g., `0`:

.. code-block:: console

    $ rio edit-info --nodata 0 example.tif


mask
----

Added in 0.21

The ``mask`` command masks in pixels from all bands of a raster using features
(masking out all areas not covered by features) and optionally crops the output
raster to the extent of the features.  Features are assumed to be in the same
coordinate reference system as the input raster.

A common use case is masking in raster data by political or other boundaries.

.. code-block:: console

    $ rio mask input.tif output.tif --geojson-mask input.geojson

GeoJSON features may be provided using stdin or specified directly as first
argument, and output can be cropped to the extent of the features.

.. code-block:: console

    $ rio mask input.tif output.tif --crop --geojson-mask - < input.geojson

The feature mask can be inverted to mask out pixels covered by features and
keep pixels not covered by features.

.. code-block:: console

    $ rio mask input.tif output.tif --invert --geojson-mask input.geojson


info
----

Added in 0.13

The ``info`` command prints structured information about a dataset.

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

More information, such as band statistics, can be had using the ``--verbose``
option.

.. code-block:: console

    $ rio info tests/data/RGB.byte.tif --indent 2 --verbose
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

The ``insp`` command opens a dataset and an interpreter.

.. code-block:: console

    $ rio insp --ipython tests/data/RGB.byte.tif
    Rasterio 0.32.0 Interactive Inspector (Python 2.7.10)
    Type "src.meta", "src.read(1)", or "help(src)" for more information.
    In [1]: print(src.name)
    /path/rasterio/tests/data/RGB.byte.tif

    In [2]: print(src.bounds)
    BoundingBox(left=101985.0, bottom=2611485.0, right=339315.0, top=2826915.0)


merge
-----

Added in 0.12.1

The ``merge`` command can be used to flatten a stack of identically structured
datasets.

.. code-block:: console

    $ rio merge rasterio/tests/data/R*.tif merged.tif


overview
--------

New in 0.25

The ``overview`` command creates overviews stored in the dataset, which can
improve performance in some applications.

The decimation levels at which to build overviews can be specified as a
comma separated list

.. code-block:: console

    $ rio overview --build 2,4,8,16

or a base and range of exponents.

.. code-block:: console

    $ rio overview --build 2^1..4

Note that overviews can not currently be removed and are not automatically
updated when the dataset's primary bands are modified.

Information about existing overviews can be printed using the --ls option.

.. code-block:: console

    $ rio overview --ls


rasterize
---------

New in 0.18.

The ``rasterize`` command rasterizes GeoJSON features into a new or existing
raster.

.. code-block:: console

    $ rio rasterize test.tif --res 0.0167 < input.geojson

The resulting file will have an upper left coordinate determined by the bounds
of the GeoJSON (in EPSG:4326, which is the default), with a
pixel size of approximately 30 arc seconds.  Pixels whose center is within the
polygon or that are selected by Bresenham's line algorithm will be burned in
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

The ``shapes`` command extracts and writes features of a specified dataset band
out as GeoJSON.

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

The ``stack`` command stacks a number of bands from one or more input files
into a multiband dataset. Input datasets must be of a kind: same data type,
dimensions, etc. The output is cloned from the first input. By default,
``stack`` will take all bands from each input and write them in same order to
the output. Optionally, bands for each input may be specified using the
following syntax:

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

You can use `--rgb` as shorthand for `--co photometric=rgb`.


transform
---------

New in 0.10.

The ``transform`` command reads a JSON array of coordinates, interleaved, and
writes another array of transformed coordinates to stdout.

To transform a longitude, latitude point (EPSG:4326 is the default) to
another coordinate system with 2 decimal places of output precision, do the
following.

.. code-block:: console

    $ echo "[-78.0, 23.0]" | rio transform - --dst-crs EPSG:32618 --precision 2
    [192457.13, 2546667.68]

To transform a longitude, latitude bounding box to the coordinate system of
a raster dataset, do the following.

.. code-block:: console

    $ echo "[-78.0, 23.0, -76.0, 25.0]" | rio transform - --dst-crs tests/data/RGB.byte.tif --precision 2
    [192457.13, 2546667.68, 399086.97, 2765319.94]


warp
----

New in 0.25

The ``warp`` command warps (reprojects) a raster based on parameters that can be
obtained from a template raster, or input directly.  The output is always
overwritten.

To copy coordinate reference system, transform, and dimensions from a template
raster, do the following:

.. code-block:: console

    $ rio warp input.tif output.tif --like template.tif

You can specify an output coordinate system using a PROJ.4 or EPSG:nnnn string,
or a JSON text-encoded PROJ.4 object:

.. code-block:: console

    $ rio warp input.tif output.tif --dst-crs EPSG:4326

    $ rio warp input.tif output.tif --dst-crs '+proj=longlat +ellps=WGS84 +datum=WGS84'

You can also specify dimensions, which will automatically calculate appropriate
resolution based on the relationship between the bounds in the target crs and
these dimensions:

.. code-block:: console

    $ rio warp input.tif output.tif --dst-crs EPSG:4326 --dimensions 100 200

Or provide output bounds (in source crs) and resolution:

.. code-block:: console

    $ rio warp input.tif output.tif --dst-crs EPSG:4326 --bounds -78 22 -76 24 --res 0.1

Other options are available, see:

.. code-block:: console

    $ rio warp --help


Rio Plugins
-----------

Rio uses ``click-plugins`` to provide the ability to create additional
subcommands using plugins developed outside rasterio.  This is ideal for
commands that require additional dependencies beyond those used by rasterio, or
that provide functionality beyond the intended scope of rasterio.

For example, `rio-mbtiles <https://github.com/mapbox/rio-mbtiles>`__ provides
a command ``rio mbtiles`` to export a raster to an MBTiles file.

See `click-plugins <https://github.com/click-contrib/click-plugins>`__ for more
information on how to build these plugins in general.

To use these plugins with rio, add the commands to the
``rasterio.rio_plugins'`` entry point in your ``setup.py`` file, as described
`here <https://github.com/click-contrib/click-plugins#developing-plugins>`__
and in ``rasterio/rio/main.py``.

See the
`plugin registry <https://github.com/mapbox/rasterio/wiki/Rio-plugin-registry>`__
for a list of available plugins.



Other commands?
---------------

Suggestions for other commands are welcome!
