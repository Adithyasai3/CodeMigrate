from django.contrib.auth.hashers import (
    PBKDF2PasswordHasher,
    SHA1PasswordHasher,
    UnsaltedMD5PasswordHasher,
)

legacy = SHA1PasswordHasher()
very_legacy = UnsaltedMD5PasswordHasher()
modern = PBKDF2PasswordHasher()
