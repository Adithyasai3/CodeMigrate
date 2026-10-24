from django.core.cache.backends.memcached import MemcachedCache

cache = MemcachedCache("127.0.0.1:11211", {})
