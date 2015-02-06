from rasterio.features import bounds


# Tests copied from Fiona 1.4.1

def test_bounds_point():
    g = {'type': 'Point', 'coordinates': [10, 10]}
    assert bounds(g) == (10, 10, 10, 10)


def test_bounds_line():
    g = {'type': 'LineString', 'coordinates': [[0, 0], [10, 10]]}
    assert bounds(g) == (0, 0, 10, 10)


def test_bounds_polygon():
    g = {'type': 'Polygon', 'coordinates': [[[0, 0], [10, 10], [10, 0]]]}
    assert bounds(g) == (0, 0, 10, 10)


def test_bounds_z():
    g = {'type': 'Point', 'coordinates': [10, 10, 10]}
    assert bounds(g) == (10, 10, 10, 10)


# TODO: add these to Fiona with update to bounds
def test_bounds_existing_bbox():
    """ Test with existing bbox in geojson, similar to that produced by
    rasterio.  Values specifically modified here for testing, bboxes are not
    valid as written.
    """

    fc = {
        'bbox': [-107, 40, -105, 41],
        'features': [{
            'bbox': [-107, 40, -104, 42],
            'geometry': {
                'coordinates': [
                    [[-107, 40], [-106, 40], [-106, 41], [-107, 41], [-107, 40]]
                ],
                'type': 'Polygon'
            },
            'type': 'Feature'
        }],
        'type': 'FeatureCollection'
    }
    assert bounds(fc['features'][0]) == (-107, 40, -104, 42)
    assert bounds(fc) == (-107, 40, -105, 41)


def test_feature_collection():
    fc = {
        'features': [{
            'geometry': {
                'coordinates': [
                    [[-107, 40], [-106, 40], [-106, 41], [-107, 41], [-107, 40]]
                ],
                'type': 'Polygon'
            },
            'type': 'Feature'
        }],
        'type': 'FeatureCollection'
    }
    assert bounds(fc['features'][0]) == (-107, 40, -106, 41)
    assert bounds(fc) == (-107, 40, -106, 41)
