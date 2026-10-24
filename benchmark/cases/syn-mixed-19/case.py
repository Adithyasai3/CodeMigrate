from django.core.validators import EmailValidator
import datetime
from django.utils.timezone import now, utc as UTC
from django.db.models.functions import TruncMonth, TruncWeek, TruncYear


from django.utils.text import slugify

SLUG = slugify('Upgrade Check')


validator = EmailValidator(whitelist=["localhost"])
allowed = validator.domain_whitelist



START = datetime.datetime(2020, 1, 1, tzinfo=UTC)
TODAY = now()


month = TruncMonth("created", is_dst=False)
week = TruncWeek("created", is_dst=False)
year = TruncYear("created")
