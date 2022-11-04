Reprojection
============

Rasterio can map the pixels of a destination raster with an associated
coordinate reference system and transform to the pixels of a source image with
a different coordinate reference system and transform. This process is known as
reprojection.

Rasterio's :func:`rasterio.warp.reproject` is a geospatial-specific analog
to SciPy's ``scipy.ndimage.interpolation.geometric_transform()`` [1]_.

The code below reprojects between two arrays, using no pre-existing GIS
datasets.  :func:`rasterio.warp.reproject` has two positional arguments: source
and destination.  The remaining keyword arguments parameterize the reprojection
transform.

.. code-block:: python

    import numpy as np
    import rasterio
    from rasterio import Affine as A
    from rasterio.warp import reproject, Resampling

    with rasterio.Env():

        # As source: a 512 x 512 raster centered on 0 degrees E and 0
        # degrees N, each pixel covering 15".
        rows, cols = src_shape = (512, 512)
        d = 1.0/240 # decimal degrees per pixel
        # The following is equivalent to
        # A(d, 0, -cols*d/2, 0, -d, rows*d/2).
        src_transform = A.translation(-cols*d/2, rows*d/2) * A.scale(d, -d)
        src_crs = {'init': 'EPSG:4326'}
        source = np.ones(src_shape, np.uint8)*255

        # Destination: a 1024 x 1024 dataset in Web Mercator (EPSG:3857)
        # with origin at 0.0, 0.0.
        dst_shape = (1024, 1024)
        dst_transform = A.translation(-237481.5, 237536.4) * A.scale(425.0, -425.0)
        dst_crs = {'init': 'EPSG:3857'}
        destination = np.zeros(dst_shape, np.uint8)

        reproject(
            source,
            destination,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)

        # Assert that the destination is only partly filled.
        assert destination.any()
        assert not destination.all()


See `examples/reproject.py <https://github.com/rasterio/rasterio/blob/master/examples/reproject.py>`__
for code that writes the destination array to a GeoTIFF file. I've uploaded the
resulting file to a Mapbox map to show that the reprojection is
correct: https://a.tiles.mapbox.com/v3/sgillies.hfek2oko/page.html?secure=1#6/0.000/0.033. (dead link)

Estimating optimal output shape
-------------------------------

Rasterio provides a :func:`rasterio.warp.calculate_default_transform` function to
determine the optimal resolution and transform for the destination raster.
Given a source dataset in a known coordinate reference system, this
function will return a ``transform, width, height`` tuple which is calculated
by libgdal.

Reprojecting a GeoTIFF dataset
------------------------------

Reprojecting a GeoTIFF dataset from one coordinate reference system is a common
use case.  Rasterio provides a few utilities to make this even easier:

:func:`~rasterio.warp.transform_bounds`
transforms the bounding coordinates of the source raster to the target
coordinate reference system, densifiying points along the edges to account
for non-linear transformations of the edges.


:func:`~rasterio.warp.calculate_default_transform`
transforms bounds to target coordinate system, calculates resolution if not
provided, and returns destination transform and dimensions.


.. code-block:: python

    import numpy as np
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, Resampling

    dst_crs = 'EPSG:4326'

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open('/tmp/RGB.byte.wgs84.tif', 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)


See ``rasterio/rio/warp.py`` for more complex examples of reprojection based on
new bounds, dimensions, and resolution (as well as a command-line interface
described :ref:`here <warp>`).

It is also possible to use :func:`~rasterio.warp.reproject` to create an output dataset zoomed
out by a factor of 2.  Methods of the :class:`rasterio.Affine` class help us generate
the output dataset's transform matrix and, thereby, its spatial extent.

.. code-block:: python

    import numpy as np
    import rasterio
    from rasterio import Affine as A
    from rasterio.warp import reproject, Resampling

    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        src_transform = src.transform

        # Zoom out by a factor of 2 from the center of the source
        # dataset. The destination transform is the product of the
        # source transform, a translation down and to the right, and
        # a scaling.
        dst_transform = src_transform*A.translation(
            -src.width/2.0, -src.height/2.0)*A.scale(2.0)

        data = src.read()

        kwargs = src.meta
        kwargs['transform'] = dst_transform

        with rasterio.open('/tmp/zoomed-out.tif', 'w', **kwargs) as dst:

            for i, band in enumerate(data, 1):
                dest = np.zeros_like(band)

                reproject(
                    band,
                    dest,
                    src_transform=src_transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=src.crs,
                    resampling=Resampling.nearest)

                dst.write(dest, indexes=i)

.. image:: https://farm8.staticflickr.com/7399/16390100651_54f01b8601_b_d.jpg)

Reprojecting with other georeferencing metadata
------------------------------------------------

Most geospatial datasets have a geotransform which can be used to reproject a dataset
from one coordinate reference system to another. Datasets may also be
georeferenced by alternative metadata, namely Ground Control Points (gcps) or
Rational Polynomial Coefficients (rpcs). For details on gcps and rpcs, see
:doc:`georeferencing`. A common scenario is using gcps or rpcs to geocode
(orthorectify) datasets, resampling and reorienting them to a coordinate
reference system with a newly computed geotransform.

.. code-block:: python

    import rasterio
    from rasterio.warp import reproject
    from rasterio.enums import Resampling

    with rasterio.open('RGB.byte.tif') as source:
        print(source.rpcs)
        src_crs = "EPSG:4326"  # This is the crs of the rpcs

        # Optional keyword arguments to be passed to GDAL transformer
        # https://gdal.org/api/gdal_alg.html?highlight=gdalcreategenimgprojtransformer2#_CPPv432GDALCreateGenImgProjTransformer212GDALDatasetH12GDALDatasetHPPc
        kwargs = {
            'RPC_DEM': '/path/to/dem.tif'
        }

        # Destination: a 1024 x 1024 dataset in Web Mercator (EPSG:3857)
        destination = np.zeros((1024, 1024), dtype=np.uint8)
        dst_crs = "EPSG:3857"

        _, dst_transform = reproject(
            source,
            destination,
            rpcs=source.rpcs,
            src_crs=src_crs,
            dst_crs=dst_crs,
            resampling=Resampling.nearest,
            **kwargs
        )

        assert destination.any()

.. note::
    When reprojecting a dataset with gcps or rpcs, the src_crs parameter should
    be supplied with the coordinate reference system that the gcps or rpcs are
    referenced against. By definition rpcs are always referenced against WGS84
    ellipsoid with geographic coordinates (EPSG:4326) [2]_.



References
----------

.. [1] https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.geometric_transform.html#scipy.ndimage.geometric_transform
.. [2] http://geotiff.maptools.org/rpc_prop.html
