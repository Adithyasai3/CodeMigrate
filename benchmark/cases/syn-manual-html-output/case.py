from django import forms


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
