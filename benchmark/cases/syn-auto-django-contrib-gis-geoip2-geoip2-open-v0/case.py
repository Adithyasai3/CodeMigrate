from django.utils import timezone

STARTED = timezone.now()

from django.contrib.gis.geoip2 import GeoIP2

MEMBER = GeoIP2.open
