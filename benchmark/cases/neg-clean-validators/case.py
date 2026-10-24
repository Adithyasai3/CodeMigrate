from django.core.validators import EmailValidator, MaxValueValidator, URLValidator

email = EmailValidator(allowlist=["localhost"])
url = URLValidator()
small = MaxValueValidator(10)
