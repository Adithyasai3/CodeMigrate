from django.utils import timezone

STARTED = timezone.now()

from django.db.models import functions

VALUE = functions.TruncDay
