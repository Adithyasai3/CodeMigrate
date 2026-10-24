from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.base import Model


class Custom(Model):
    def run(self):
        return self.asave()
