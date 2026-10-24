from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from django.utils import baseconv
from django.contrib.sitemaps import Sitemap, SitemapNotFound, ping_google


from django.utils import timezone

STARTED = timezone.now()


month = TruncMonth("created", is_dst=False)
week = TruncWeek("created", is_dst=False)
year = TruncYear("created")


encoded = baseconv.base62.encode(12345)



class StaticSitemap(Sitemap):
    def items(self):
        return []


HANDLERS = (ping_google, SitemapNotFound)
