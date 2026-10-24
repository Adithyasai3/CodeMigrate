from django.db.models import DateTimeField
from django.db.models.functions import Trunc, TruncDay

by_day = Trunc("created", "day", output_field=DateTimeField())
by_day2 = TruncDay("created")
