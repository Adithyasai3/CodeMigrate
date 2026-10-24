from django.db.models import Q

ACTIVE = Q(is_active=True)

from django.test.testcases import TransactionTestCase


class Custom(TransactionTestCase):
    def run(self):
        return self.assertQuerysetEqual()
