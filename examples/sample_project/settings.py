SECRET_KEY = "dev"
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "shop"]
USE_L10N = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.SHA1PasswordHasher"]
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
