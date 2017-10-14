"""Tests for ``$ rio rm``."""


import pytest

import rasterio
import rasterio.shutil
from rasterio.rio.main import main_group


@pytest.mark.parametrize("driver", (None, 'GTiff'))
def test_rm(runner, driver, path_rgb_byte_tif, tmpdir):

    path = str(tmpdir.join('test_rm.tif'))
    rasterio.shutil.copy(path_rgb_byte_tif, path)

    args = ['rm', path, '--yes']
    if driver is not None:
        args.extend(['--driver', driver])

    result = runner.invoke(main_group, args)
    assert result.exit_code == 0
    assert not rasterio.shutil.exists(path), path


def test_rm_invalid_dataset(runner):

    """Invalid dataset."""

    result = runner.invoke(main_group, ['rm', 'trash', '--yes'])
    assert result.exit_code != 0
    assert "Invalid dataset: trash" in result.output


def test_rm_invalid_driver(runner, tmpdir, path_rgb_byte_tif):

    """Valid dataset invalid driver."""

    path = str(tmpdir.join('test_rm_invalid_driver.tif'))
    rasterio.shutil.copy(path_rgb_byte_tif, path)

    result = runner.invoke(
        main_group, ['rm', path, '--driver', 'trash', '--yes'])
    assert result.exit_code != 0
    assert "Unrecognized driver: trash" in result.output

    # File still exists since test failed.  Cleanup.
    rasterio.shutil.delete(path)
