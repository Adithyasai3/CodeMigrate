from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.core.files.storage import get_storage_class

VALUE = get_storage_class
