from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.auth.hashers import CryptPasswordHasher

VALUE = CryptPasswordHasher
