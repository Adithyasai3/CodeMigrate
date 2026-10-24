from django.db.models import DateTimeField
from django.db.models.functions import Trunc, TruncDay, TruncHour
from django.http.multipartparser import parse_header
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME, checkbox


from django.db.models import Q

ACTIVE = Q(is_active=True)


by_day = Trunc("created", "day", output_field=DateTimeField(), is_dst=False)
by_day2 = TruncDay("created", is_dst=True)
by_hour = TruncHour("created")


content_type, params = parse_header(b"text/plain; charset=utf-8")


WIDGET = checkbox
NAME = ACTION_CHECKBOX_NAME
