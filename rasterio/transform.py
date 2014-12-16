import warnings

from affine import Affine

IDENTITY = Affine.identity()


def tastes_like_gdal(seq):
    """Return True if `seq` matches the GDAL geotransform pattern."""
    return seq[2] == seq[4] == 0.0 and seq[1] > 0 and seq[5] < 0


def guard_transform(transform):
    """Return an Affine transformation instance"""
    if not isinstance(transform, Affine):
        if tastes_like_gdal(transform):
            warnings.warn(
                "GDAL-style transforms are deprecated and will not "
                "be supported in Rasterio 1.0.",
                FutureWarning,
                stacklevel=2)
            transform = Affine.from_gdal(*transform)
        else:
            transform = Affine(*transform)
    return transform
