from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.forms.forms import BaseForm


class Custom(BaseForm):
    def run(self):
        return self._html_output()
