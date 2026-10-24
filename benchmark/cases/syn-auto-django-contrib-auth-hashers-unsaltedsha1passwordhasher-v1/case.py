from django.utils import timezone

STARTED = timezone.now()

from django.contrib.auth import hashers

VALUE = hashers.UnsaltedSHA1PasswordHasher
