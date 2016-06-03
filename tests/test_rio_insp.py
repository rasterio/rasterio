"""Unittests for $ rio insp and public API."""


import numpy as np
import pytest

import rasterio
from rasterio.rio.main import main_group
from rasterio.rio.insp import stats


def test_insp(runner):
    result = runner.invoke(main_group, ['insp', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0


def test_insp_err(runner):
    result = runner.invoke(main_group, ['insp', 'tests'])
    assert result.exit_code == 1


def test_bad_interpreter():
    from rasterio.rio.insp import main
    with rasterio.open("tests/data/RGB.byte.tif", 'r') as src:
        with pytest.raises(ValueError):
            main("Test banner", src, "PHP")


def test_stats():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        results = stats((src, 1))
        assert results[0] == 0
        assert results[1] == 255
        assert np.isclose(results[2], 29.9477)

        results2 = stats(src.read(1))
        assert np.allclose(np.array(results), np.array(results2))
