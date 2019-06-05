"""Tests of dataset connection sharing"""

import rasterio

from .conftest import requires_gdal2


@requires_gdal2
def test_sharing_on(capfd, path_rgb_byte_tif):
    """Datasets are shared"""
    with rasterio.Env() as env:

        # Opens a new file.
        with rasterio.open(path_rgb_byte_tif, sharing=False) as srcx:
            env._dump_open_datasets()
            captured = capfd.readouterr()
            assert "1 N GTiff" in captured.err
            assert "1 S GTiff" not in captured.err

            # Does not open a new file.
            with rasterio.open(path_rgb_byte_tif, sharing=True) as srcy:
                env._dump_open_datasets()
                captured = capfd.readouterr()
                assert "1 N GTiff" in captured.err
                assert "1 S GTiff" in captured.err


@requires_gdal2
def test_sharing_off(capfd, path_rgb_byte_tif):
    """Datasets are not shared"""
    with rasterio.Env() as env:

        # Opens a new file.
        with rasterio.open(path_rgb_byte_tif, sharing=False) as srcx:
            env._dump_open_datasets()
            captured = capfd.readouterr()
            assert "1 N GTiff" in captured.err
            assert "1 S GTiff" not in captured.err

            # Does not open a new file.
            with rasterio.open(path_rgb_byte_tif, sharing=False) as srcy:
                env._dump_open_datasets()
                captured = capfd.readouterr()
                assert captured.err.count("1 N GTiff") == 2
                assert "1 S GTiff" not in captured.err
