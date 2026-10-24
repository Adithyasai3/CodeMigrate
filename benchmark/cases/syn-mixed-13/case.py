from django.utils.html import format_html
from django.test import SimpleTestCase
from django.utils.functional import cached_property


from django.db.models import Q

ACTIVE = Q(is_active=True)


banner = format_html("<b>Static banner</b>")
greeting = format_html("<i>{}</i>", "hi")


CHECKER = SimpleTestCase.assertFormsetError
OTHER = SimpleTestCase.assertFormError



class Box:
    def _area(self):
        return 4

    area = cached_property(_area, name="area")


BOX = Box()
