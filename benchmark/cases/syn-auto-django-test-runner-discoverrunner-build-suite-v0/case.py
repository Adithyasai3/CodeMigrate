import logging

logger = logging.getLogger(__name__)

from django.test.runner import DiscoverRunner

MEMBER = DiscoverRunner.build_suite
