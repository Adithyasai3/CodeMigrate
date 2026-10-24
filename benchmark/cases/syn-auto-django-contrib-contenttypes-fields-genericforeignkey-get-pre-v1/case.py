import logging

logger = logging.getLogger(__name__)

from django.contrib.contenttypes.fields import GenericForeignKey


class Custom(GenericForeignKey):
    def run(self):
        return self.get_prefetch_queryset()
