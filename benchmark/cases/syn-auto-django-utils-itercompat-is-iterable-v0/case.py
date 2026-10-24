import logging

logger = logging.getLogger(__name__)

from django.utils.itercompat import is_iterable

VALUE = is_iterable
