Quick example of getting all bands as appropriately masked arrays.

.. code-block:: python

    import numpy
    import rasterio


    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        b, g, r = (
            numpy.ma.masked_equal(
                src.read_band(src.indexes[i]), 
                src.nodatavals[i]) 
            for i in range(3))

    print(b)
    print(b.mask)
    print(b.fill_value)
    print(b.min(), b.max(), b.mean())

Output:

.. code-block:: console

    [[-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     ...,
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]
     [-- -- -- ..., -- -- --]]
    [[ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     ...,
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]
     [ True  True  True ...,  True  True  True]]
    0
    (1, 255, 44.434478650699106)

