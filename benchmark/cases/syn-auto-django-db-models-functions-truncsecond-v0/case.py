import logging

logger = logging.getLogger(__name__)

from django.db.models.functions import TruncSecond

VALUE = TruncSecond
