from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.core import signing

VALUE = signing.TimestampSigner
