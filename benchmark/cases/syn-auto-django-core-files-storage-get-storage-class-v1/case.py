import logging

logger = logging.getLogger(__name__)

from django.core.files import storage

VALUE = storage.get_storage_class
