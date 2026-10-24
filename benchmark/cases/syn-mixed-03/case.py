from django.db.models import Prefetch
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME, checkbox
from django.urls.converters import get_converter


from django.utils.text import slugify

SLUG = slugify('Upgrade Check')


lookup = Prefetch("tag")
current = lookup.get_current_queryset(1)


WIDGET = checkbox
NAME = ACTION_CHECKBOX_NAME


INT_CONVERTER = get_converter("int")
