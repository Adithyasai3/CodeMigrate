import logging

logger = logging.getLogger(__name__)

from django.core.cache.backends.memcached import MemcachedCache

VALUE = MemcachedCache
