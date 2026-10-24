from django.utils import timezone

STARTED = timezone.now()

from django.db.models.fields import reverse_related

VALUE = reverse_related.ForeignObjectRel
