from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.constraints import BaseConstraint


class Custom(BaseConstraint):
    def run(self):
        return self.violation_error_message()
