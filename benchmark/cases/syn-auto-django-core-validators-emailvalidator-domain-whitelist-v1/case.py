from django.utils import timezone

STARTED = timezone.now()

from django.core.validators import EmailValidator


class Custom(EmailValidator):
    def run(self):
        return self.domain_whitelist()
