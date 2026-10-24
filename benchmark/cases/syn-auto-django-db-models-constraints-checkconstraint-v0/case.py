import logging

logger = logging.getLogger(__name__)

from django.db.models.constraints import CheckConstraint

VALUE = CheckConstraint
