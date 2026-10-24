from django.utils import timezone

STARTED = timezone.now()

from django.contrib.auth.hashers import UnsaltedMD5PasswordHasher

VALUE = UnsaltedMD5PasswordHasher
