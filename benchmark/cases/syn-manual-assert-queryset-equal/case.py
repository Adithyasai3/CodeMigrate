from django.test import TransactionTestCase


class Checks(TransactionTestCase):
    def runTest(self):
        pass


CASE = Checks()
CASE.assertQuerysetEqual([1, 2], [1, 2])
CASE.assertEqual(1, 1)
