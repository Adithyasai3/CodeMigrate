import datetime
from django.utils import timezone
from django.test import TransactionTestCase
from django.core.files.storage import get_storage_class


import logging

logger = logging.getLogger(__name__)



EPOCH = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
NOW = timezone.now()



class Checks(TransactionTestCase):
    def runTest(self):
        pass


CASE = Checks()
CASE.assertQuerysetEqual([1, 2], [1, 2])
CASE.assertEqual(1, 1)


StorageClass = get_storage_class("django.core.files.storage.FileSystemStorage")
storage = StorageClass(location="/tmp")
