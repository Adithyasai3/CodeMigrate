from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.query import QuerySet


class Custom(QuerySet):
    def run(self):
        return self.iterator()
