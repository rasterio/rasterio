
from collections import namedtuple


class AffineMatrix(
        namedtuple('AffineMatrix',  ('a', 'b', 'c', 'd', 'e', 'f'))):
    """
    The augmented affine transformation matrix.

      | x' |   | a  b  c | | x |
      | y' | = | d  e  f | | y |
      | 1  |   | 0  0  1 | | 1 |

    The vector on the left hand side is position in world coordinates
    and the vector on the right hand side, image/array coordinates.

    Note that c and f are the world coordinates at the image/array
    origin (upper left corner).
    """

    @classmethod
    def from_gdal(self, c, a, b, f, d, e):
        return AffineMatrix(a, b, c, d, e, f)

    def to_gdal(self):
        return (self.c, self.a, self.b, self.f, self.d, self.e)

    @property
    def xoff(self):
        return self.c

    @property
    def yoff(self):
        return self.f


BoundingBox = namedtuple('BoundingBox', ('left', 'bottom', 'right', 'top'))

