from django.utils import timezone

STARTED = timezone.now()

from django.contrib.admin import ModelAdmin

MEMBER = ModelAdmin.lookup_allowed
