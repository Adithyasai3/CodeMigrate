from django.core.cache.backends.locmem import LocMemCache

cache = LocMemCache("default", {})
cache.set("k", 1)
VALUE = cache.get("k")
