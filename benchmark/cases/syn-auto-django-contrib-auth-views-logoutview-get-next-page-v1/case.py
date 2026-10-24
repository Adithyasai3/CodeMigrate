from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.contrib.auth.views import LogoutView


class Custom(LogoutView):
    def run(self):
        return self.get_next_page()
