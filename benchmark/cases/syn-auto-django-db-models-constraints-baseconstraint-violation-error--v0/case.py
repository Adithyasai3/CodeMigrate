from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.db.models.constraints import BaseConstraint

MEMBER = BaseConstraint.violation_error_message
