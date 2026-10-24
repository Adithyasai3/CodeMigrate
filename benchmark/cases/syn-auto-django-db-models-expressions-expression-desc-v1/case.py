from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.models.expressions import Expression


class Custom(Expression):
    def run(self):
        return self.desc()
