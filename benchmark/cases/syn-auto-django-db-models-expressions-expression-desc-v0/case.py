import logging

logger = logging.getLogger(__name__)

from django.db.models.expressions import Expression

MEMBER = Expression.desc
