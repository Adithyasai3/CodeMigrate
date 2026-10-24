from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.http.multipartparser import parse_header

VALUE = parse_header
