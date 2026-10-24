from django.utils import timezone

STARTED = timezone.now()

from django.contrib.admin.options import ModelAdmin

MEMBER = ModelAdmin.log_deletion
