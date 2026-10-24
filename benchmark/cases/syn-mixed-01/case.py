from django import forms
from django.core.files.storage import get_storage_class
from django.core.cache.backends.memcached import MemcachedCache


import logging

logger = logging.getLogger(__name__)



class ContactForm(forms.Form):
    name = forms.CharField()


FORM = ContactForm()
HTML = FORM._html_output(
    normal_row="<p>%(field)s</p>",
    error_row="%s",
    row_ender="</p>",
    help_text_html=" %s",
    errors_on_separate_row=False,
)


StorageClass = get_storage_class("django.core.files.storage.FileSystemStorage")
storage = StorageClass(location="/tmp")


cache = MemcachedCache("127.0.0.1:11211", {})
