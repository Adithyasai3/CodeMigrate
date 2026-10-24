from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.backends.mysql.features import DatabaseFeatures

MEMBER = DatabaseFeatures.allows_group_by_pk
