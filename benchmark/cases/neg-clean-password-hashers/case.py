from django.contrib.auth.hashers import PBKDF2PasswordHasher, make_password

hasher = PBKDF2PasswordHasher()
HASHED = make_password("secret", hasher="pbkdf2_sha256")
