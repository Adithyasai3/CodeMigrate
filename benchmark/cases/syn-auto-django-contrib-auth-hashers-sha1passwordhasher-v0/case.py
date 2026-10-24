from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.auth.hashers import SHA1PasswordHasher

VALUE = SHA1PasswordHasher
