from django.utils import timezone

STARTED = timezone.now()

from django.db.models.query import QuerySet

MEMBER = QuerySet.iterator
