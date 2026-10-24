from django.utils import timezone

STARTED = timezone.now()

from django.contrib.auth.backends import RemoteUserBackend


class Custom(RemoteUserBackend):
    def run(self):
        return self.configure_user()
