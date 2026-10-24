SECRET_KEY = "x"
DEBUG = False
USE_TZ = True
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
MIDDLEWARE = ["django.middleware.common.CommonMiddleware"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
