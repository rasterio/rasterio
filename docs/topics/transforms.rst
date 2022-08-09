Transforms
===========

Rasterio supports three primary methods for transforming of coordinates from 
image pixel (row, col) to and from geographic/projected (x, y) coordinates.
The interface for performing these coordinate transformations is available 
in :mod:`rasterio.transform` through one of :class:`.AffineTransformer`,
:class:`.GCPTransformer`, or :class:`.RPCTransformer`.
The methods :meth:`~.DatasetReader.xy` and :meth:`~rasterio.transform.rowcol`
are responsible for converting between (row, col) -> (x, y) and (x, y) ->
(row, col), respectively. 

Using Affine transformation matrix
-----------------------------------
:class:`.AffineTransformer` takes care of coordinate transformations
given an Affine transformation matrix. For example

.. code-block:: python

    >>> transform = Affine(300.0379266750948, 0.0, 101985.0, 0.0,
                           -300.041782729805, 2826915.0)
    >>> transformer = rasterio.transform.AffineTransformer(transform)
    >>> transformer.xy(0, 0)
    (102135.01896333754, 2826764.979108635)
    >>> transformer.rowcol(102135.01896333754, 2826764.979108635)
    (0, 0)

This is approximately equivalent to

.. code-block:: python

    >>> transform = Affine(300.0379266750948, 0.0, 101985.0, 0.0,
                           -300.041782729805, 2826915.0)
    >>> transform * (0.5, 0.5)
    (102135.01896333754, 2826764.979108635)
    >>> ~transform * (102135.01896333754, 2826764.979108635)
    (0.5, 0.5)

The dataset methods :meth:`~.DatasetReader.xy` and :meth:`~.DatasetReader.index` use :mod:`rasterio.transform` under the hood

.. code-block:: python

    >>> with rasterio.open('RGB.byte.tif') as src:
            print(src.xy(0, 0))
    (102135.01896333754, 2826764.979108635)

Using Ground Control Points
----------------------------

.. code-block:: python

    >>> gcps = [GroundControlPoint(row=11521.5, col=0.5, x=-123.6185142817931, y=48.99561141948625, z=89.13533782958984, id='217', info=''),
                GroundControlPoint(row=11521.5, col=7448.5, x=-122.8802747777599, y=48.91210259315549, z=89.13533782958984, id='234', info=''),
                GroundControlPoint(row=0.5, col=0.5, x=-123.4809665720148, y=49.52809729106944, z=89.13533782958984, id='1', info=''),
                GroundControlPoint(row=0.5, col=7448.5, x=-122.7345733674704, y=49.44455878004666, z=89.13533782958984, id='18', info='')]
    >>> transformer = rasterio.transform.GCPTransformer(gcps)
    >>> transformer.xy(0, 0)
    (-123.478928146887, 49.52808986989645)

Using Rational Polynomial Coefficients
---------------------------------------
For accuracy a height value is typically required when using :class:`.RPCTransformer`. By default,
a value of 0 is assumed. 

.. code-block:: python

    >>> with rasterio.open('RGB.byte.rpc.vrt') as src:
            transformer = rasterio.trasform.RPCTransformer(src.rpcs)
            transformer.xy(0, 0)
    (-123.47959047080701, 49.52794990575094)

A first order correction would be to use a mean elevation value for the image

.. code-block:: python

    >>> with rasterio.open('RGB.byte.rpc.vrt') as src:
            transformer = rasterio.trasform.RPCTransformer(src.rpcs)
            transformer.xy(0, 0, zs=src.rpcs.height_off)
    (-123.48096552376548, 49.528097381526386)

Better yet is to sample height values from a digital elevation model (DEM). 
:class:`.RPCTransformer` allows for options to be passed to :cpp:func:`GDALCreateRPCTransformerV2`

.. code-block:: python

    >>> with rasterio.open('RGB.byte.rpc.vrt') as src:
            transformer = rasterio.trasform.RPCTransformer(src.rpcs, rpc_dem='vancouver-dem.tif')
            transformer.xy(0, 0)
    (-123.47954729595642, 49.5279448909449)

Transformer Resources
----------------------
The :class:`.AffineTransformer` is a pure Python class, however :class:`.GCPTransformer`
and :class:`.RPCTransformer` make use of C/C++ GDAL objects. Explicit control of 
the transformer object can be achieved by use within a context manager or 
by calling ``close()`` method e.g.

.. code-block:: python

    >>> with rasterio.transform.RPCTransformer(rpcs) as transform:
            transform.xy(0, 0)
    >>> transform.xy(0, 0)
    ValueError: Unexpected NULL transformer

.. note::
    If ``RPC_DEM`` is specified in ``rpc_options``, GDAL will maintain an
    open file handle to the DEM until the transformer is closed.