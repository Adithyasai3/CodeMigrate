from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.forms.utils import ErrorList

VALUE = ErrorList
