"""VSIFile tests."""

import pytest

from rasterio.io import VSIFile, MemoryFile


def test_offset(path_rgb_byte_tif):
    with VSIFile(path_rgb_byte_tif) as vsifile:
        assert vsifile.tell() == 0


def test_closed(path_rgb_byte_tif):
    """A closed VSIFile can not be opened"""
    with VSIFile(path_rgb_byte_tif) as vsifile:
        pass
    with pytest.raises(IOError):
        vsifile.open()


def test_VSI_open(path_rgb_byte_tif):
    """VSIFile contents can initialized and opened."""
    with VSIFile(path_rgb_byte_tif) as vsifile:
        with vsifile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_read_bytes(path_rgb_byte_tif):
    """VSIFile can read file content."""
    with VSIFile(path_rgb_byte_tif) as vsifile, open(path_rgb_byte_tif, "rb") as f:
        assert vsifile.read(100) == f.read(100)


def test_seek(path_rgb_byte_tif):
    """VSIFile contents can move offset, read content and be opened."""
    with VSIFile(path_rgb_byte_tif) as vsifile, open(path_rgb_byte_tif, "rb") as f:
        vsifile.seek(600000)
        assert vsifile.tell() == 600000
        f.seek(600000)
        assert vsifile.read(100) == f.read(100)
        with vsifile.open() as src:
            assert src.driver == "GTiff"
            assert src.count == 3
            assert src.dtypes == ("uint8", "uint8", "uint8")
            assert src.read().shape == (3, 718, 791)


def test_with_vsi_input(path_rgb_byte_tif):
    """VSIFile can read vsimem file."""
    with open(path_rgb_byte_tif, "rb") as f:
        with MemoryFile(f.read()) as mem:
            f.seek(0)
            with VSIFile(mem.name) as vsifile:
                assert vsifile.read(100) == f.read(100)
                with vsifile.open() as src:
                    assert src.driver == "GTiff"
                    assert src.count == 3
                    assert src.dtypes == ("uint8", "uint8", "uint8")
                    assert src.read().shape == (3, 718, 791)
