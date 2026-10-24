from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.models.functions import TruncMinute

VALUE = TruncMinute
