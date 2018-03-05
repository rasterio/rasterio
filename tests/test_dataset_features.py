import pytest

import rasterio
from rasterio.features import dataset_features


def test_feature_(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = list(dataset_features(src=src, bidx=1))

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_badbidx(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        with pytest.raises(ValueError):
            list(dataset_features(
                src=src,
                bidx=99))


def test_feature_nodata(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=1,
            sampling=1,
            band=True,
            as_mask=False,
            with_nodata=True,
            geographic=True,
            precision=-1)

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_sampling(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=1,
            sampling=4)

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_as_mask(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=1,
            as_mask=True)

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_as_mask_nodata(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=1,
            as_mask=True,
            with_nodata=True)

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_precision(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=1,
            precision=2)

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_not_geographic(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=1,
            geographic=False)

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_not_band(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=1,
            band=False,
            sampling=2)

        for f in features:
            assert f['type'] == 'Feature'


def test_feature_not_band_not_bidx(pixelated_image_file):
    with rasterio.open(pixelated_image_file) as src:
        features = dataset_features(
            src=src,
            bidx=None,
            band=False,
            sampling=2)

        for f in features:
            assert f['type'] == 'Feature'
