from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.admin import helpers

VALUE = helpers.checkbox
