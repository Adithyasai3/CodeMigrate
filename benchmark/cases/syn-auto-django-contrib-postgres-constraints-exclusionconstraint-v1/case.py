from django.utils import timezone

STARTED = timezone.now()

from django.contrib.postgres import constraints

VALUE = constraints.ExclusionConstraint
