from django.utils import timezone

STARTED = timezone.now()

from django.db.backends.mysql.features import DatabaseFeatures


class Custom(DatabaseFeatures):
    def run(self):
        return self.allows_group_by_pk()
