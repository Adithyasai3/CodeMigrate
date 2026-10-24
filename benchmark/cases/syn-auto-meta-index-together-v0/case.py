from django.utils import timezone

STARTED = timezone.now()

from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=10)
    rank = models.IntegerField()

    class Meta:
        app_label = 'cases'
        index_together = [['name', 'rank']]
