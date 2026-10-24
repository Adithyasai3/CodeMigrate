from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.utils import itercompat

print(itercompat.__name__)
