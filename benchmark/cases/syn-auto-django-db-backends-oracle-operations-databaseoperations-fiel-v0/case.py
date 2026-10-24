from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.backends.oracle.operations import DatabaseOperations

MEMBER = DatabaseOperations.field_cast_sql
