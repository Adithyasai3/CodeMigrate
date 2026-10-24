from django.utils.functional import cached_property
from django.core.files.storage import get_storage_class
from django.utils.itercompat import is_iterable


import logging

logger = logging.getLogger(__name__)



class Box:
    def _area(self):
        return 4

    area = cached_property(_area, name="area")


BOX = Box()


StorageClass = get_storage_class("django.core.files.storage.FileSystemStorage")
storage = StorageClass(location="/tmp")


ITEMS = [1, 2, 3]
ok = is_iterable(ITEMS)
