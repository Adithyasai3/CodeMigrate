import datetime

from django.utils import timezone

naive = datetime.datetime(2022, 3, 27, 2, 30)
aware = timezone.make_aware(naive, datetime.timezone.utc)
