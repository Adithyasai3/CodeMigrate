from django.utils import timezone

STARTED = timezone.now()

from django.contrib.auth.backends import RemoteUserBackend

MEMBER = RemoteUserBackend.configure_user
