from django.utils import timezone

STARTED = timezone.now()

from django.core.cache.backends import memcached

VALUE = memcached.MemcachedCache
