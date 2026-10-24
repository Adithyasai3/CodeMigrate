from django.db.models import Count, F, Q, Value

FILTER = Q(active=True) | Q(staff=True)
ORDER = F("created").desc(nulls_last=True)
ANNOTATION = Count("id")
LABEL = Value("x")
