from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.sitemaps.views import SitemapIndexItem

MEMBER = SitemapIndexItem.__str__
