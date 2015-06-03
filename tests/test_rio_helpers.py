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
