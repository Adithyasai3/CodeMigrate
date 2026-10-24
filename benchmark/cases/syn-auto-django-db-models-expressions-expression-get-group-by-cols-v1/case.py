from django.utils import timezone

STARTED = timezone.now()

from django.db.models.expressions import Expression


class Custom(Expression):
    def run(self):
        return self.get_group_by_cols()
