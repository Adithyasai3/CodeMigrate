from django.db.models import CheckConstraint, Q, UniqueConstraint

adult = CheckConstraint(check=Q(age__gte=18), name="adult")
unique_email = UniqueConstraint(fields=["email"], name="unique_email")
