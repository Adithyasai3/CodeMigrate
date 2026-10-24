from django.utils import timezone

STARTED = timezone.now()

from django.contrib.gis.gdal.geometries import OGRGeometry


class Custom(OGRGeometry):
    def run(self):
        return self.coord_dim()
