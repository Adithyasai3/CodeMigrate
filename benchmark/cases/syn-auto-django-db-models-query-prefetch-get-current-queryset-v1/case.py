from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.query import Prefetch


class Custom(Prefetch):
    def run(self):
        return self.get_current_queryset()
