from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.forms.models import BaseModelFormSet


class Custom(BaseModelFormSet):
    def run(self):
        return self.save_existing()
