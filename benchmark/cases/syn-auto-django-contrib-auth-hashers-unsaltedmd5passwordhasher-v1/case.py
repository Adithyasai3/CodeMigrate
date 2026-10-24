from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.auth import hashers

VALUE = hashers.UnsaltedMD5PasswordHasher
