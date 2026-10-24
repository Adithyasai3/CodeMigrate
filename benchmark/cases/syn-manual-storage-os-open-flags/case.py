from django.core.files.storage import FileSystemStorage

storage = FileSystemStorage(location="/tmp")
FLAGS = storage.OS_OPEN_FLAGS
