from django.utils.text import slugify

SLUG = slugify('Upgrade Check')

from django.test.testcases import TransactionTestCase

MEMBER = TransactionTestCase.assertQuerysetEqual
