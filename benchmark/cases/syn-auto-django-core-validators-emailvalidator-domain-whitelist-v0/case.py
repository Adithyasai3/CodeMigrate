import logging

logger = logging.getLogger(__name__)

from django.core.validators import EmailValidator

MEMBER = EmailValidator.domain_whitelist
