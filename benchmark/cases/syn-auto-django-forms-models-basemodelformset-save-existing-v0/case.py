from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.forms.models import BaseModelFormSet

MEMBER = BaseModelFormSet.save_existing
