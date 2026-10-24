from django.utils import timezone

STARTED = timezone.now()

from django.contrib.admin import ModelAdmin


class Custom(ModelAdmin):
    def run(self):
        return self.lookup_allowed()
