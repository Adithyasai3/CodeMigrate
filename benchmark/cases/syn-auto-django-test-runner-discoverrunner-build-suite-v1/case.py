from django.utils import timezone

STARTED = timezone.now()

from django.test.runner import DiscoverRunner


class Custom(DiscoverRunner):
    def run(self):
        return self.build_suite()
