import logging

logger = logging.getLogger(__name__)

from django.contrib.postgres.constraints import ExclusionConstraint

VALUE = ExclusionConstraint
