from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.postgres.fields import CIEmailField

VALUE = CIEmailField
