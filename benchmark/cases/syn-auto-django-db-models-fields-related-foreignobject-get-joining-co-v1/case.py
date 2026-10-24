from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.db.models.fields.related import ForeignObject


class Custom(ForeignObject):
    def run(self):
        return self.get_joining_columns()
