from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.backends.dummy.base import DatabaseIntrospection


class Custom(DatabaseIntrospection):
    def run(self):
        return self.get_key_columns()
