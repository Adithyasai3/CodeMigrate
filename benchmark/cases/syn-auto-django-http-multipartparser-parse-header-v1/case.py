import logging

logger = logging.getLogger(__name__)

from django.http import multipartparser

VALUE = multipartparser.parse_header
