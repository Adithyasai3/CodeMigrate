from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.postgres.fields import CICharField

VALUE = CICharField
