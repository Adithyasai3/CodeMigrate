from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.gis.forms import BaseGeometryWidget


class Custom(BaseGeometryWidget):
    def run(self):
        return self.map_width()
