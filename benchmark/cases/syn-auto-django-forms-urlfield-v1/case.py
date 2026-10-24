from django.db.models import Q

ACTIVE = Q(is_active=True)

from django import forms

VALUE = forms.URLField
