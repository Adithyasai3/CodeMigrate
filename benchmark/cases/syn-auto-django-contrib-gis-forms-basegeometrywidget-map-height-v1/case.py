from django.utils import timezone

STARTED = timezone.now()

from django.contrib.gis.forms import BaseGeometryWidget


class Custom(BaseGeometryWidget):
    def run(self):
        return self.map_height()
