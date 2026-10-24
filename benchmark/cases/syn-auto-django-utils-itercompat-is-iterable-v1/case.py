import logging

logger = logging.getLogger(__name__)

from django.utils import itercompat

VALUE = itercompat.is_iterable
