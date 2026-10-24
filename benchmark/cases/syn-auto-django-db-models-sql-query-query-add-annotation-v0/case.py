from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.sql.query import Query

MEMBER = Query.add_annotation
