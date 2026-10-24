from django.db import models


class Event(models.Model):
    kind = models.CharField(max_length=20)
    at = models.DateTimeField()

    class Meta:
        app_label = "sessions"
        indexes = [models.Index(fields=["kind"])]
        index_together = (("kind", "at"),)
