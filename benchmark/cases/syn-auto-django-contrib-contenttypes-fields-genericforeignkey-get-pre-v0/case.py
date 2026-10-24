import logging

logger = logging.getLogger(__name__)

from django.contrib.contenttypes.fields import GenericForeignKey

MEMBER = GenericForeignKey.get_prefetch_queryset
