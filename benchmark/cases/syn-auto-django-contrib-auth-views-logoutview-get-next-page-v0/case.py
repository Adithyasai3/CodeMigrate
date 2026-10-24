from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.auth.views import LogoutView

MEMBER = LogoutView.get_next_page
