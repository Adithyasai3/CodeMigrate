from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.fields.related import ForeignObject


class Custom(ForeignObject):
    def run(self):
        return self.get_reverse_joining_columns()
