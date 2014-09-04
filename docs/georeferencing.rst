Georeferencing
==============

There are two parts to the georeferencing of raster datasets: the definition
of the local, regional, or global system in which a raster's pixels are
located; and the parameters by which pixel coordinates are transformed into
coordinates in that system.

Coordinate Reference System
---------------------------

The coordinate reference system of a dataset is accessed from its ``crs``
attribute. Type ``rio insp tests/data/RGB.byte.tif`` from the 
Rasterio distribution root to see.

.. code-block:: pycon

    Rasterio 0.9 Interactive Inspector (Python 3.4.1)
    Type "src.meta", "src.read_band(1)", or "help(src)" for more information.
    >>> src
    <open RasterReader name='tests/data/RGB.byte.tif' mode='r'>
    >>> src.crs
    {'init': 'epsg:32618'}

Rasterio follows pyproj and uses PROJ.4 syntax in dict form as its native
CRS syntax. If you want a WKT representation of the CRS, see the ``crs_wkt``
attribute.

.. code-block:: pycon

    >>> src.crs_wkt
    'PROJCS["UTM Zone 18, Northern Hemisphere",GEOGCS["Unknown datum based upon the WGS 84 ellipsoid",DATUM["Not_specified_based_on_WGS_84_spheroid",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-75],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","32618"]]'

When opening a new file for writing, you may also use a CRS string as an
argument.

.. code-block:: pycon

   >>> with rasterio.open('/tmp/foo.tif', 'w', crs='EPSG:3857', ...) as dst:
   ...     # write data to this Web Mercator projection dataset.

Coordinate Transformation
-------------------------

A dataset's pixel coordinate system has its orgin at the "upper left" (imagine
it displayed on your screen). Column index increases to the right, and row 
index increases downward. The mapping of these coordinates to "world"
coordinates in the dataset's reference system is done with an affine
transformation matrix.

.. code-block:: pycon

    >>> src.affine
    Affine(300.0379266750948, 0.0, 101985.0,
           0.0, -300.041782729805, 2826915.0)

The ``Affine`` object is a named tuple with elements ``a, b, c, d, e, f``
corresponding to the elements in the matrix equation below, in which 
a pixel's image coordinates are ``x, y`` and its world coordinates are
``x', y'``.::

    | x' |   | a b c | | x |
    | y' | = | d e f | | y |
    | 1  |   | 0 0 1 | | 1 |

The ``Affine`` class has a number of useful properties and methods
described at https://github.com/sgillies/affine.

The ``affine`` attribute is new. Previous versions of Rasterio had only a
``transform`` attribute. As explained in the warning below, Rasterio is in
a transitional phase.

.. code-block:: pycon

    >>> src.transform
    /usr/local/Cellar/python3/3.4.1/Frameworks/Python.framework/Versions/3.4/lib/python3.4/code.py:90: FutureWarning: The value of this property will change in version 1.0. Please see https://github.com/mapbox/rasterio/issues/86 for details.
    [101985.0, 300.0379266750948, 0.0, 2826915.0, 0.0, -300.041782729805]

In Rasterio 1.0, the value of a  ``transform`` attribute will be an instance
of ``Affine`` and the ``affine`` attribute will remain as an alias.

