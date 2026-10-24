from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.auth.base_user import BaseUserManager

MEMBER = BaseUserManager.make_random_password
