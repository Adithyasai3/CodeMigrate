from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.backends.dummy.base import DatabaseIntrospection

MEMBER = DatabaseIntrospection.get_key_columns
