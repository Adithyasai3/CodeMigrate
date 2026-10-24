from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.gis.geoip2 import GeoIP2


class Custom(GeoIP2):
    def run(self):
        return self.coords()
