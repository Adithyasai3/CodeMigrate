from django.db.models import F, OrderBy

newest = F("created").desc(nulls_last=False)
oldest = F("created").asc(nulls_first=False)
explicit = OrderBy(F("created"), nulls_first=False)
fine = F("created").asc(nulls_last=True)
