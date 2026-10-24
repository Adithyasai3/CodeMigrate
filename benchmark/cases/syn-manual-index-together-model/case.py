from django.db import models


class Visit(models.Model):
    path = models.CharField(max_length=200)
    day = models.DateField()

    class Meta:
        app_label = "sessions"
        index_together = [["path", "day"]]
