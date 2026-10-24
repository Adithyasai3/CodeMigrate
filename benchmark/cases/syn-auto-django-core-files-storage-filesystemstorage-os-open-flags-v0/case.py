from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.core.files.storage import FileSystemStorage

MEMBER = FileSystemStorage.OS_OPEN_FLAGS
