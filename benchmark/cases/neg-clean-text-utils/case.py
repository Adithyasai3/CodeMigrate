from django.utils.text import capfirst, slugify, Truncator

SLUG = slugify("Hello World")
CAP = capfirst("django")
SHORT = Truncator("long text here").chars(5)
