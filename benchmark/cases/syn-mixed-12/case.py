from django.views.static import was_modified_since
from django.core.validators import EmailValidator
from django.contrib.auth.hashers import (


from django.utils.text import slugify

SLUG = slugify('Upgrade Check')


MODIFIED = was_modified_since(None, 0, 0)


validator = EmailValidator(whitelist=["localhost"])
allowed = validator.domain_whitelist

    PBKDF2PasswordHasher,
    SHA1PasswordHasher,
    UnsaltedMD5PasswordHasher,
)

legacy = SHA1PasswordHasher()
very_legacy = UnsaltedMD5PasswordHasher()
modern = PBKDF2PasswordHasher()
