from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.utils import html

VALUE = html.format_html
