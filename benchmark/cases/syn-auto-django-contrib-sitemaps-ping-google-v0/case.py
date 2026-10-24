import logging

logger = logging.getLogger(__name__)

from django.contrib.sitemaps import ping_google

VALUE = ping_google
