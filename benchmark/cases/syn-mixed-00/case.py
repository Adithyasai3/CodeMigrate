from django.db.models.functions import TruncMonth, TruncWeek, TruncYear
from django.db import models
from django.contrib.auth.hashers import CryptPasswordHasher


import logging

logger = logging.getLogger(__name__)


month = TruncMonth("created", is_dst=False)
week = TruncWeek("created", is_dst=False)
year = TruncYear("created")



class Event(models.Model):
    kind = models.CharField(max_length=20)
    at = models.DateTimeField()

    class Meta:
        app_label = "sessions"
        indexes = [models.Index(fields=["kind"])]
        index_together = (("kind", "at"),)


hasher = CryptPasswordHasher()
algorithm = hasher.algorithm
