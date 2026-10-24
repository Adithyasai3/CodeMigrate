import datetime

from django.utils.timezone import now, utc as UTC

START = datetime.datetime(2020, 1, 1, tzinfo=UTC)
TODAY = now()
