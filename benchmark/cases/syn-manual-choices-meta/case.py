from django.db import models
from django.db.models.enums import ChoicesMeta


class Color(models.TextChoices):
    RED = "r", "Red"


IS_META = isinstance(Color, ChoicesMeta)
