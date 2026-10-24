from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.gis import forms

VALUE = forms.BaseGeometryWidget
