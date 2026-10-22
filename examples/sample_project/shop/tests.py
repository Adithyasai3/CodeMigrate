from django.test import TestCase

from .models import Order


class OrderTests(TestCase):
    def test_listing(self):
        self.assertQuerysetEqual(Order.objects.none(), [])
