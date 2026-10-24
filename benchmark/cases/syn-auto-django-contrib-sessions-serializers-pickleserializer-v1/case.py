from django.utils import timezone

STARTED = timezone.now()

from django.contrib.sessions import serializers

VALUE = serializers.PickleSerializer
