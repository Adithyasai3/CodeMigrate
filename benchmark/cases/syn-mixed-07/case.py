import datetime
from django.utils import timezone
from django.db import models
from django.db.models.enums import ChoicesMeta
from django.urls import register_converter


from django.utils import timezone

STARTED = timezone.now()



EPOCH = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
NOW = timezone.now()



class Color(models.TextChoices):
    RED = "r", "Red"


IS_META = isinstance(Color, ChoicesMeta)



class FourDigitYear:
    regex = "[0-9]{4}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return "%04d" % value


register_converter(FourDigitYear, "yyyy")
register_converter(FourDigitYear, "int")
