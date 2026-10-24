from django.utils import timezone

STARTED = timezone.now()

from django.db.models.functions import TruncQuarter

VALUE = TruncQuarter
