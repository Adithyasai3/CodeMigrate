from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.utils.html import format_html

VALUE = format_html
