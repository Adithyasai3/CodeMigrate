from django.core.files.storage import get_storage_class
from django.core.cache.backends.memcached import MemcachedCache
from django.contrib.auth.base_user import BaseUserManager


from django.db.models import Q

ACTIVE = Q(is_active=True)


StorageClass = get_storage_class("django.core.files.storage.FileSystemStorage")
storage = StorageClass(location="/tmp")


cache = MemcachedCache("127.0.0.1:11211", {})


manager = BaseUserManager()
password = manager.make_random_password(length=12)
