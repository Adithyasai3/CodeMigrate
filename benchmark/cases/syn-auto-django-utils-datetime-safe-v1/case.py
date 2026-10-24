from django.db.models import Q

ACTIVE = Q(is_active=True)

import django.utils.datetime_safe as mod

print(mod.__name__)
