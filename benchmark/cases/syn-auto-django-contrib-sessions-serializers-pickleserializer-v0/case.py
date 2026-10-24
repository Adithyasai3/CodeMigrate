from django.utils import timezone

STARTED = timezone.now()

from django.contrib.sessions.serializers import PickleSerializer

VALUE = PickleSerializer
