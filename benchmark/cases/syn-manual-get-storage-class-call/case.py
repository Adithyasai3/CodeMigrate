from django.core.files.storage import get_storage_class

StorageClass = get_storage_class("django.core.files.storage.FileSystemStorage")
storage = StorageClass(location="/tmp")
