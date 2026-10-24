from django.db.models import Prefetch

lookup = Prefetch("tag")
current = lookup.get_current_queryset(1)
