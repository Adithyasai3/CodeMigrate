from django.db.models import DateTimeField
from django.db.models.functions import Trunc, TruncDay, TruncHour

by_day = Trunc("created", "day", output_field=DateTimeField(), is_dst=False)
by_day2 = TruncDay("created", is_dst=True)
by_hour = TruncHour("created")
