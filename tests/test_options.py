import click
import pytest
from rasterio.rio import options


def test_cb_key_val():

    pairs = ['KEY=val', '1==']
    expected = {
        'KEY': 'val',
        '1': '=',
    }
    assert options._cb_key_val(None, None, pairs) == expected

    # Make sure None or an empty list returns an empty dict
    assert options._cb_key_val(None, None, None) == {}
    assert options._cb_key_val(None, None, ()) == {}

    with pytest.raises(click.BadParameter):
        options._cb_key_val(None, None, 'bad_val')
