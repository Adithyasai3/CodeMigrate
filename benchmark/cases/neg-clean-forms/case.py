from django import forms


class SignupForm(forms.Form):
    email = forms.EmailField()
    age = forms.IntegerField(min_value=0)


FORM = SignupForm(data={"email": "a@example.com", "age": 3})
OK = FORM.is_valid()
