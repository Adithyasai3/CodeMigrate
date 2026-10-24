from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.test.testcases import SimpleTestCase


class Custom(SimpleTestCase):
    def run(self):
        return self.assertFormError()
