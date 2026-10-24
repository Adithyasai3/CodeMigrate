from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.sitemaps.views import SitemapIndexItem


class Custom(SitemapIndexItem):
    def run(self):
        return self.__str__()
