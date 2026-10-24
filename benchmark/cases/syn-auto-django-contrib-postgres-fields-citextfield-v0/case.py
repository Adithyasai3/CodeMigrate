from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.postgres.fields import CITextField

VALUE = CITextField
