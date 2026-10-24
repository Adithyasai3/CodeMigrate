from django.db.models.functions import TruncMonth, TruncWeek, TruncYear

month = TruncMonth("created", is_dst=False)
week = TruncWeek("created", is_dst=False)
year = TruncYear("created")
