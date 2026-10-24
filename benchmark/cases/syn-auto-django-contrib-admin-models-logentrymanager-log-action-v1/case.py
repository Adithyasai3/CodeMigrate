from django.utils import timezone

STARTED = timezone.now()

from django.contrib.admin.models import LogEntryManager


class Custom(LogEntryManager):
    def run(self):
        return self.log_action()
