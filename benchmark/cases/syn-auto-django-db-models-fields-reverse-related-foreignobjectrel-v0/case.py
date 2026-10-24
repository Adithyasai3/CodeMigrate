import logging

logger = logging.getLogger(__name__)

from django.db.models.fields.reverse_related import ForeignObjectRel

VALUE = ForeignObjectRel
