from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models import functions

VALUE = functions.TruncYear
