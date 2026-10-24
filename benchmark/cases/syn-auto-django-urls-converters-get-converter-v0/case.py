from django.utils import timezone

STARTED = timezone.now()

from django.urls.converters import get_converter

VALUE = get_converter
