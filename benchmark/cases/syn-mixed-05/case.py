from django.contrib.auth.hashers import CryptPasswordHasher
from django.core.files.storage import get_storage_class
from django.contrib.auth.hashers import (


import logging

logger = logging.getLogger(__name__)


hasher = CryptPasswordHasher()
algorithm = hasher.algorithm


StorageClass = get_storage_class("django.core.files.storage.FileSystemStorage")
storage = StorageClass(location="/tmp")

    PBKDF2PasswordHasher,
    SHA1PasswordHasher,
    UnsaltedMD5PasswordHasher,
)

legacy = SHA1PasswordHasher()
very_legacy = UnsaltedMD5PasswordHasher()
modern = PBKDF2PasswordHasher()
