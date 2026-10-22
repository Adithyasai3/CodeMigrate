from django.db import models
from django.utils import timezone


class Order(models.Model):
    created = models.DateTimeField(default=timezone.now)
    code = models.CharField(max_length=20)

    class Meta:
        index_together = [["code", "created"]]

    def created_utc(self):
        return self.created.astimezone(timezone.utc)
