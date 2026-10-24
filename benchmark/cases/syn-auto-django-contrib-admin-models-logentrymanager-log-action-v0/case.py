from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.admin.models import LogEntryManager

MEMBER = LogEntryManager.log_action
