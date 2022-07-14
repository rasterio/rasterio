Error Handling
==============

.. todo::

    error enums, context managers, converting GDAL errors to python exceptions


Debugging Internal GDAL
------------------------

To get more debugging information from the internal GDAL code:

1. Enable the `CPL_DEBUG` config option.

    .. code-block:: python

        with rasterio.Env(CPL_DEBUG=True):
            ...


2. Activate logging in `rasterio` with the devel `DEBUG`:

    More information available here: https://docs.python.org/3/howto/logging.html

    Here are examples to get started.

    Add handler to the `rasterio` logger:

    .. code-block:: python

        import logging

        console_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(levelname)s:%(message)s")
        console_handler.setFormatter(formatter)
        logger = logging.getLogger("rasterio")
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)


    Activate default logging config:

    .. code-block:: python

        import logging

        logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)
