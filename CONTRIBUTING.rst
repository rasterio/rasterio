Welcome to the Rasterio project. Here's how we work.

Code of Conduct
---------------

First of all: the Rasterio project has a code of conduct. Please read the
CODE_OF_CONDUCT.txt file, it's important to all of us.

Rights
------

The BSD license (see LICENSE.txt) applies to all contributions.

Issue Conventions
-----------------

Rasterio is a relatively new project and highly active. We have bugs, both
known and unknown.

Please search existing issues, open and closed, before creating a new one.

Rasterio employs C extension modules, so bug reports very often hinge on the
following details:

- Operating system type and version (Windows? Ubuntu 12.04? 14.04?)
- The version and source of Rasterio (PyPI, Anaconda, or somewhere else?)
- The version and source of GDAL (UbuntuGIS? Homebrew?)

Please provide these details as well as tracebacks and relevant logs.  When
using the ``$ rio`` CLI logging can be enabled with ``$ rio -v`` and verbosity
can be increased with ``-vvv``.  Short scripts and datasets demonstrating the
issue are especially helpful!

Rasterio is not at 1.0 yet and issues proposing new features are welcome.

Design Principles
-----------------

Rasterio's API is different from GDAL's API and this is intentional.

- Rasterio is a library for reading and writing raster datasets. Rasterio uses
  GDAL but is not a "Python binding for GDAL."
- Rasterio always prefers Python's built-in protocols and types or Numpy
  protocols and types over concepts from GDAL's data model.
- Rasterio keeps I/O separate from other operations. ``rasterio.open()`` is
  the only library function that operates on filenames and URIs.
  ``dataset.read()``, ``dataset.write()``, and their mask counterparts are
  the methods that perform I/O.
- Rasterio methods and functions should be free of side-effects and hidden
  inputs. This is challenging in practice because GDAL embraces global
  variables.

Dataset Objects
---------------

Our term for the kind of object that allows read and write access to raster data
is *dataset object*. A dataset object might be an instance of `DatasetReader`
or `DatasetWriter`. The canonical way to create a dataset object is by using the
`rasterio.open()` function.

This is analogous to Python's use of 
`file object <https://docs.python.org/3/glossary.html#term-file-object>`__.

Git Conventions
---------------

We use a variant of centralized workflow described in the `Git Book
<https://git-scm.com/book/en/v2/Distributed-Git-Distributed-Workflows>`__.  We
have no 1.0 release for Rasterio yet and we are tagging and releasing from the
master branch. Our post-1.0 workflow is to be decided.

Work on features in a new branch of the mapbox/rasterio repo or in a branch on
a fork. Create a `GitHub pull request
<https://help.github.com/articles/using-pull-requests/>`__ when the changes are
ready for review.  We recommend creating a pull request as early as possible
to give other developers a heads up and to provide an opportunity for valuable
early feedback.

Code Conventions
----------------

The ``rasterio`` namespace contains both Python and C extension modules. All
C extension modules are written using `Cython <http://cython.org/>`__. The
Cython language is a superset of Python. Cython files end with ``.pyx`` and
``.pxd`` and are where we keep all the code that calls GDAL's C functions.

Rasterio supports Python 2 and Python 3 in the same code base, which is
aided by an internal compatibility module named ``compat.py``. It functions
similarly to the more widely known `six <https://pythonhosted.org/six/>`__ but
we only use a small portion of the features so it eliminates a dependency.

We strongly prefer code adhering to `PEP8
<https://www.python.org/dev/peps/pep-0008/>`__.

Tests are mandatory for new features. We use `pytest <https://pytest.org>`__.

We aspire to 100% coverage for Python modules but coverage of the Cython code is
a future aspiration (`#515 <https://github.com/mapbox/rasterio/issues/515>`__).

Development Environment
-----------------------

Developing Rasterio requires Python 2.7 or any final release after and
including 3.4.  We prefer developing with the most recent version of Python
but recognize this is not possible for all contributors.  A C compiler is also
required to leverage `existing protocols
<https://docs.python.org/3.5/extending/extending.html>`__ for extending Python
with C or C++.  See the Windows install instructions in the `readme
<README.rst>`__ for more information about building on Windows.

Initial Setup
^^^^^^^^^^^^^

First, clone Rasterio's ``git`` repo:

.. code-block:: console

    $ git clone https://github.com/mapbox/rasterio

Development should occur within a `virtual environment
<http://docs.python-guide.org/en/latest/dev/virtualenvs/>`__ to better isolate
development work from custom environments.

In some cases installing a library with an accompanying executable inside a
virtual environment causes the shell to initially look outside the environment
for the executable.  If this occurs try deactivating and reactivating the
environment.

Installing GDAL
^^^^^^^^^^^^^^^

The GDAL library and its headers are required to build Rasterio. We do not
have currently have guidance for any platforms other than Linux and OS X.

On Linux, GDAL and its headers should be available through your distro's
package manager. For Ubuntu the commands are:

.. code-block:: console

    $ sudo add-apt-repository ppa:ubuntugis/ppa
    $ sudo apt-get update
    $ sudo apt-get install gdal-bin libgdal-dev

On OS X, Homebrew is a reliable way to get GDAL.

.. code-block:: console

    $ brew install gdal

Python build requirements
^^^^^^^^^^^^^^^^^^^^^^^^^

Provision a virtualenv with Rasterio's build requirements.  Rasterio's
``setup.py`` script will not run unless Cython and Numpy are installed, so do
this first from the Rasterio repo directory.

Linux users may need to install some additional Numpy dependencies:

.. code-block:: console

    $ sudo apt-get install libatlas-dev libatlas-base-dev gfortran

then:

.. code-block:: console

    $ pip install -U pip
    $ pip install -r requirements-dev.txt

Installing Rasterio
^^^^^^^^^^^^^^^^^^^

Rasterio, its Cython extensions, normal dependencies, and dev dependencies can
be installed with ``$ pip``.  Installing Rasterio in editable mode while
developing is very convenient but only affects the Python files.  Specifying the
``[test]`` extra in the command below tells ``$ pip`` to also install
Rasterio's dev dependencies.

.. code-block:: console

    $ pip install -e .[test]

Any time a Cython (``.pyx`` or ``.pxd``) file is edited the extension modules
need to be recompiled, which is most easily achieved with:

.. code-block:: console

    $ pip install -e .

When switching between Python versions the extension modules must be recompiled,
which can be forced with ``$ touch rasterio/*.pyx`` and then re-installing with
the command above.  If this is not done an error claiming that an object ``has
the wrong size, try recompiling`` is raised.

The dependencies required to build the docs can be installed with:

.. code-block:: console

    $ pip install -e .[docs]

Running the tests
^^^^^^^^^^^^^^^^^

Rasterio's tests live in ``tests <tests/>`` and generally match the main
package layout.

To run the entire suite and the code coverage report:

.. code-block:: console

    $ py.test --cov rasterio --cov-report term-missing

A single test file:

.. code-block:: console

    $ py.test tests/test_band.py

A single test:

.. code-block:: console

    $ py.test tests/test_band.py::test_band
