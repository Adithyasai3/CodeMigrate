from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.contrib.auth.base_user import BaseUserManager


class Custom(BaseUserManager):
    def run(self):
        return self.make_random_password()
