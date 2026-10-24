import logging

logger = logging.getLogger(__name__)

from django.db.models.fields.related import ForeignObject

MEMBER = ForeignObject.get_joining_columns
