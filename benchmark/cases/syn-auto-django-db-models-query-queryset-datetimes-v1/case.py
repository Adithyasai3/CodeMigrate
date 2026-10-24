import logging

logger = logging.getLogger(__name__)

from django.db.models.query import QuerySet


class Custom(QuerySet):
    def run(self):
        return self.datetimes()
