from django.db.models import F, OrderBy

a = F("created").asc(nulls_last=True)
b = OrderBy(F("created"), nulls_first=True)
