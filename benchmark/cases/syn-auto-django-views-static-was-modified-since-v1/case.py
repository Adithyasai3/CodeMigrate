from django.utils import timezone

STARTED = timezone.now()

from django.views import static

VALUE = static.was_modified_since
