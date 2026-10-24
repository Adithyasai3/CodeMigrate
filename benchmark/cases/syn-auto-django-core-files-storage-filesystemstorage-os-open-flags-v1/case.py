import logging

logger = logging.getLogger(__name__)

from django.core.files.storage import FileSystemStorage


class Custom(FileSystemStorage):
    def run(self):
        return self.OS_OPEN_FLAGS()
