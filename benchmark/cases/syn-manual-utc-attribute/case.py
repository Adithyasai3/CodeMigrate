import datetime

from django.utils import timezone

EPOCH = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
NOW = timezone.now()
