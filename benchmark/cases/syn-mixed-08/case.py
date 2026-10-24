from django.utils.functional import cached_property
import datetime
from django.utils.timezone import now, utc as UTC
from django.db import models
from django.db.models.enums import ChoicesMeta


from django.utils import timezone

STARTED = timezone.now()



class Box:
    def _area(self):
        return 4

    area = cached_property(_area, name="area")


BOX = Box()



START = datetime.datetime(2020, 1, 1, tzinfo=UTC)
TODAY = now()



class Color(models.TextChoices):
    RED = "r", "Red"


IS_META = isinstance(Color, ChoicesMeta)
