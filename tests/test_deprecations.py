# TODO delete this in 1.0
# This ensures that deprecation warnings are given but behavior is maintained
# on the way to stabilizing the API for 1.0
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


def test_data_window_unmasked(data):
    with pytest.warns(DeprecationWarning):
        old = get_data_window(data)
    new = windows.get_data_window(data)
    assert old == new


def test_windows_intersect_disjunct():
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]

    with pytest.warns(DeprecationWarning):
        old = windows_intersect(data)
    new = windows.intersect(data)
    assert old == new


def test_window_intersection():
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]

    with pytest.warns(DeprecationWarning):
        old = window_intersection(data)
    new = windows.intersection(data)
    assert old == new


def test_window_union():
    data = [
        ((0, 6), (3, 6)),
        ((2, 4), (1, 5))]

    with pytest.warns(DeprecationWarning):
        old = window_union(data)
    new = windows.union(data)
    assert old == new
