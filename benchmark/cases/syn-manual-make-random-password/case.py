from django.contrib.auth.base_user import BaseUserManager

manager = BaseUserManager()
password = manager.make_random_password(length=12)
