from django.utils import timezone

STARTED = timezone.now()

from django.db.models import Model


class Custom(Model):
    def run(self):
        return self.save()
