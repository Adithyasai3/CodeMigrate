import logging

logger = logging.getLogger(__name__)

from django.db.models.fields.related import RelatedField


class Custom(RelatedField):
    def run(self):
        return self.get_cache_name()
