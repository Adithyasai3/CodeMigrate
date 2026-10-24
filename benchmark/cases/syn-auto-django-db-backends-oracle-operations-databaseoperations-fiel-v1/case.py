from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.backends.oracle.operations import DatabaseOperations


class Custom(DatabaseOperations):
    def run(self):
        return self.field_cast_sql()
