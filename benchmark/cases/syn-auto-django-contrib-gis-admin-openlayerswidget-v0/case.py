from django.utils import timezone

STARTED = timezone.now()

from django.contrib.gis.admin import OpenLayersWidget

VALUE = OpenLayersWidget
