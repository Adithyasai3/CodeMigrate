from django.utils import timezone

STARTED = timezone.now()

from django.contrib.postgres import fields

VALUE = fields.CIText
