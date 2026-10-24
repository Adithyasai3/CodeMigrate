from django.contrib.sitemaps import Sitemap, SitemapNotFound, ping_google


class StaticSitemap(Sitemap):
    def items(self):
        return []


HANDLERS = (ping_google, SitemapNotFound)
