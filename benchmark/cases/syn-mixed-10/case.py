from django.views.static import was_modified_since
from django.core.files.storage import get_storage_class
import datetime
from django.utils.timezone import now, utc as UTC


from django.utils import timezone

STARTED = timezone.now()


MODIFIED = was_modified_since(None, 0, 0)


StorageClass = get_storage_class("django.core.files.storage.FileSystemStorage")
storage = StorageClass(location="/tmp")



START = datetime.datetime(2020, 1, 1, tzinfo=UTC)
TODAY = now()
