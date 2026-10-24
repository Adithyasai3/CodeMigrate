from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.gis.forms import BaseGeometryWidget

MEMBER = BaseGeometryWidget.map_height
