import logging

logger = logging.getLogger(__name__)

from django.db.models.fields.related import RelatedField

MEMBER = RelatedField.get_cache_name
