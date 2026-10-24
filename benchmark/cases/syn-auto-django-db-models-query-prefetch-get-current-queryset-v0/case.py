from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.query import Prefetch

MEMBER = Prefetch.get_current_queryset
