"""Common classes for rasterio tests."""


class MockGeoInterface:
    """Tiny wrapper for GeoJSON to present an object with __geo_interface__ for testing"""

    def __init__(self, geojson):
        self.__geo_interface__ = geojson
