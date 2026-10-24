from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.postgres import fields

VALUE = fields.CIEmailField
