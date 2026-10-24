from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.models.sql.query import Query


class Custom(Query):
    def run(self):
        return self.add_annotation()
