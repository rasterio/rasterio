# TODO delete this in 1.0
# This ensures that deprecation warnings are given but behavior is maintained
# on the way to stabilizing the API for 1.0
import warnings

import pytest
import numpy

# New modules
from rasterio import windows

# Deprecated modules
from rasterio import (
    get_data_window, window_intersection, window_union, windows_intersect
)


DATA_WINDOW = ((3, 5), (2, 6))


@pytest.fixture
def data():
    data = numpy.zeros((10, 10), dtype='uint8')
    data[slice(*DATA_WINDOW[0]), slice(*DATA_WINDOW[1])] = 1
    return data


def test_data_window_unmasked(data, recwarn):
    warnings.simplefilter('always')
    old = get_data_window(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.get_data_window(data)
    assert len(recwarn) == 0
    assert old == new


def test_windows_intersect_disjunct(recwarn):
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]
    warnings.simplefilter('always')
    old = windows_intersect(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.intersect(data)
    assert len(recwarn) == 0
    assert old == new


def test_window_intersection(recwarn):
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]
    warnings.simplefilter('always')
    old = window_intersection(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.intersection(data)
    assert len(recwarn) == 0
    assert old == new


def test_window_union(recwarn):
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]
    warnings.simplefilter('always')
    old = window_union(data)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    new = windows.union(data)
    assert len(recwarn) == 0
    assert old == new
