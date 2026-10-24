from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.fields.related import ForeignObject

MEMBER = ForeignObject.get_reverse_joining_columns
