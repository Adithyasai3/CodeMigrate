from django import forms
from django.db import models
from django.db.models.enums import ChoicesMeta
from django.core.signing import Signer, TimestampSigner


from django.utils import timezone

STARTED = timezone.now()



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



class Color(models.TextChoices):
    RED = "r", "Red"


IS_META = isinstance(Color, ChoicesMeta)


signer = Signer("secret-key-1", ":")
stamp = TimestampSigner("secret-key-2")
token = signer.sign("hello")
