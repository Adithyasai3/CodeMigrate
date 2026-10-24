from django.test import TransactionTestCase
import datetime
from django.utils import datetime_safe
from django import forms


import logging

logger = logging.getLogger(__name__)



class Checks(TransactionTestCase):
    def runTest(self):
        pass


CASE = Checks()
CASE.assertQuerysetEqual([1, 2], [1, 2])
CASE.assertEqual(1, 1)



stamp = datetime_safe.new_datetime(datetime.datetime(1850, 1, 1))



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
