from django.utils import timezone

STARTED = timezone.now()

from django.contrib.admin.options import ModelAdmin


class Custom(ModelAdmin):
    def run(self):
        return self.log_deletion()
