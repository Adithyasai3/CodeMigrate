from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.models.query import QuerySet

MEMBER = QuerySet.datetimes
