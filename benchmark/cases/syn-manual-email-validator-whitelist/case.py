from django.core.validators import EmailValidator

validator = EmailValidator(whitelist=["localhost"])
allowed = validator.domain_whitelist
