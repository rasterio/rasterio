In-Memory Files
===============

Other sections of this documentation have explained how Rasterio can access
data stored in existing files on disk written by other programs or write files
to be used by other GIS programs. Filenames have been the typical inputs and
files on disk have been the typical outputs.

.. code-block:: python

   with rasterio.open('example.tif') as dataset:
       data_array = dataset.read()

There are different options for Python programs that have streams of bytes,
e.g., from a network socket, as their input or output instead of filenames.
One is the use of a temporary file on disk.

.. code-block:: python

    import tempfile


    with tempfile.NamedTemporaryFile() as tmpfile:
        tmpfile.write(data)
        with rasterio.open(tmpfile.name) as dataset:
            data_array = dataset.read()

Another is Rasterio's ``MemoryFile``, an abstraction for objects in GDAL's
in-memory filesystem.

MemoryFile: BytesIO meets NamedTemporaryFile
--------------------------------------------

The ``MemoryFile`` class behaves a bit like ``BytesIO`` and
``NamedTemporaryFile``.  A GeoTIFF file in a sequence of ``data`` bytes can be
opened in memory as shown below.

.. code-block:: python

   from rasterio.io import MemoryFile


    with MemoryFile(data) as memfile:
        with memfile.open() as dataset:
            data_array = dataset.read()

This code can be several times faster than the code using
``NamedTemporaryFile`` at roughly double the price in memory.

Writing MemoryFiles
-------------------

Incremental writes to an empty ``MemoryFile`` are also possible.

.. code-block:: python

    with MemoryFile() as memfile:
        while True:
            data = f.read(8192)  # ``f`` is an input stream.
            if not data:
                break
            memfile.write(data)
        with memfile.open() as dataset:
            data_array = dataset.read()

These two modes are incompatible: a ``MemoryFile`` initialized with a sequence
of bytes cannot be extended.

An empty ``MemoryFile`` can also be written to using dataset API methods.

.. code-block:: python

   with MemoryFile() as memfile:
       with memfile.open(driver='GTiff', count=3, ...) as dataset:
           dataset.write(data_array)

Reading MemoryFiles
-------------------

Like ``BytesIO``, ``MemoryFile`` implements the Python file protocol and
provides ``read()``, ``seek()``, and ``tell()`` methods. Instances are thus suitable
as arguments for methods like `requests.post() <https://requests.readthedocs.io/en/latest/api/#requests.post>`__.

.. code-block:: python

   with MemoryFile() as memfile:
       with memfile.open(driver='GTiff', count=3, ...) as dataset:
           dataset.write(data_array)

        requests.post('https://example.com/upload', data=memfile)
