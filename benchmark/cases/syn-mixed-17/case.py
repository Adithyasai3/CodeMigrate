from django.contrib.auth.views import LogoutView
from django.contrib.sessions.serializers import PickleSerializer
from django.utils.html import format_html


from django.utils.text import slugify

SLUG = slugify('Upgrade Check')



class SiteLogoutView(LogoutView):
    def get_next_page(self):
        return "/goodbye/"


payload = PickleSerializer().dumps({"cart": [1, 2]})


banner = format_html("<b>Static banner</b>")
greeting = format_html("<i>{}</i>", "hi")
