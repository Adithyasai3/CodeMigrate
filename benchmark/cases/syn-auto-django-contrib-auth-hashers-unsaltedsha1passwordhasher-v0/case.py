from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.auth.hashers import UnsaltedSHA1PasswordHasher

VALUE = UnsaltedSHA1PasswordHasher
