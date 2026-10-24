from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.test.testcases import SimpleTestCase


class Custom(SimpleTestCase):
    def run(self):
        return self.assertFormSetError()
