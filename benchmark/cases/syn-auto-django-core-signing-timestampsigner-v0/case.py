import logging

logger = logging.getLogger(__name__)

from django.core.signing import TimestampSigner

VALUE = TimestampSigner
