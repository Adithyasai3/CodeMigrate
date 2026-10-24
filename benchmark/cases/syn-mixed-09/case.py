from django.contrib.auth.hashers import (
from django.db import models


from django.utils import timezone

STARTED = timezone.now()

    PBKDF2PasswordHasher,
    SHA1PasswordHasher,
    UnsaltedMD5PasswordHasher,
)

legacy = SHA1PasswordHasher()
very_legacy = UnsaltedMD5PasswordHasher()
modern = PBKDF2PasswordHasher()



class Event(models.Model):
    kind = models.CharField(max_length=20)
    at = models.DateTimeField()

    class Meta:
        app_label = "sessions"
        indexes = [models.Index(fields=["kind"])]
        index_together = (("kind", "at"),)



class Visit(models.Model):
    path = models.CharField(max_length=200)
    day = models.DateField()

    class Meta:
        app_label = "sessions"
        index_together = [["path", "day"]]
