from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.postgres import fields

VALUE = fields.CICharField
