from django.utils import timezone

STARTED = timezone.now()

from django.utils.functional import cached_property

VALUE = cached_property
