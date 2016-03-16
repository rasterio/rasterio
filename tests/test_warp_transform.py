import rasterio
from rasterio._warp import _calculate_default_transform
from rasterio.transform import Affine, from_bounds


def test_indentity():
    """Get the same transform and dimensions back for same crs."""
    # Tile: [53, 96, 8]
    # [-11740727.544603072, 4852834.0517692715, -11584184.510675032, 5009377.085697309]
    src_crs = dst_crs = 'EPSG:3857'
    width = height = 1000
    left, bottom, right, top = (
        -11740727.544603072, 4852834.0517692715, -11584184.510675032,
        5009377.085697309)
    transform = from_bounds(left, bottom, right, top, width, height)

    with rasterio.drivers():
        res_transform, res_width, res_height = _calculate_default_transform(
            src_crs, dst_crs, width, height, left, bottom, right, top)

    assert res_width == width
    assert res_height == height
    for res, exp in zip(res_transform, transform):
        assert round(res, 7) == round(exp, 7)


def test_gdal_transform_notnull():
    with rasterio.drivers():
        dt, dw, dh = _calculate_default_transform(
            src_crs={'init': 'EPSG:4326'},
            dst_crs={'init': 'EPSG:32610'},
            width=80,
            height=80,
            left=-120,
            bottom=30,
            right=-80,
            top=70)
    assert True
