from django import forms


class ProfileForm(forms.Form):
    name = forms.CharField(max_length=50)
    homepage = forms.URLField(required=False)


FORM = ProfileForm(data={"name": "a", "homepage": "example.com"})
VALID = FORM.is_valid()
