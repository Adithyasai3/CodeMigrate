from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.functions import TruncWeek

VALUE = TruncWeek
