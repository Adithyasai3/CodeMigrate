import logging

logger = logging.getLogger(__name__)

from django.contrib.gis.forms import BaseGeometryWidget

MEMBER = BaseGeometryWidget.map_width
