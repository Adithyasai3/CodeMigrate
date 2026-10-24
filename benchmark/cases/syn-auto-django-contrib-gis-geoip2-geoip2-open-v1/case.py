from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.gis.geoip2 import GeoIP2


class Custom(GeoIP2):
    def run(self):
        return self.open()
