"""Test of CLI helpers"""

import click
import pytest

from rasterio.errors import FileOverwriteError
from rasterio.rio import helpers


def test_resolve_files_inout__output():
    assert helpers.resolve_inout(input='in', output='out') == ('out', ['in'])


def test_resolve_files_inout__input():
    assert helpers.resolve_inout(input='in') == (None, ['in'])


def test_resolve_files_inout__inout_files():
    assert helpers.resolve_inout(files=('a', 'b', 'c')) == ('c', ['a', 'b'])


def test_resolve_files_inout__inout_files_output_o():
    assert helpers.resolve_inout(
        files=('a', 'b', 'c'), output='out') == ('out', ['a', 'b', 'c'])


def test_resolve_files_insufficient_inputs():
    with pytest.raises(click.BadParameter) as excinfo:
        helpers.resolve_inout(files=["a"], num_inputs=1)
    assert "Insufficient inputs" in str(excinfo.value)


def test_resolve_files_too_many_inputs():
    with pytest.raises(click.BadParameter) as excinfo:
        helpers.resolve_inout(files=["a", "b", "c"], num_inputs=1)
    assert "Too many inputs" in str(excinfo.value)


def test_fail_overwrite(tmpdir):
    """Unforced overwrite of existing file fails."""
    foo_tif = tmpdir.join('foo.tif')
    foo_tif.write("content")
    with pytest.raises(FileOverwriteError) as excinfo:
        helpers.resolve_inout(files=[str(x) for x in tmpdir.listdir()])
        assert "file exists and won't be overwritten without use of the " in str(excinfo.value)


def test_overwrite(tmpdir):
    """Forced overwrite of existing file succeeds."""
    foo_tif = tmpdir.join('foo.tif')
    foo_tif.write("content")
    output, inputs = helpers.resolve_inout(
        files=[str(x) for x in tmpdir.listdir()], overwrite=True)
    assert output == str(foo_tif)


def test_implicit_overwrite(tmpdir):
    """Implicit overwrite of existing file fails."""
    foo_tif = tmpdir.join('foo.tif')
    foo_tif.write("content")
    with pytest.raises(FileOverwriteError):
        helpers.resolve_inout(output=str(foo_tif))


def test_to_lower():
    assert helpers.to_lower(None, None, 'EPSG:3857') == 'epsg:3857'
