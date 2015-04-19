import functools
import operator
import os
import shutil
import sys

from click.testing import CliRunner
import py
import pytest


if sys.version_info > (3,):
    reduce = functools.reduce

test_files = [os.path.join(os.path.dirname(__file__), p) for p in [
    'data/RGB.byte.tif', 'data/float.tif', 'data/float_nan.tif', 'data/shade.tif']]


def pytest_cmdline_main(config):
    # Bail if the test raster data is not present. Test data is not 
    # distributed with sdists since 0.12.
    if reduce(operator.and_, map(os.path.exists, test_files)):
        print("Test data present.")
    else:
        print("Test data not present. See download directions in tests/README.txt")
        sys.exit(1)


@pytest.fixture(scope='function')
def runner():
    return CliRunner()


@pytest.fixture(scope='function')
def data():
    """A temporary directory containing a copy of the files in data."""
    tmpdir = py.test.ensuretemp('tests/data')
    for filename in test_files:
        shutil.copy(filename, str(tmpdir))
    return tmpdir
