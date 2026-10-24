from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.sitemaps import Sitemap


class Custom(Sitemap):
    def run(self):
        return self.location()
