import datetime

from django.db import models
from django.http import JsonResponse
from django.utils.timezone import utc


class Order(models.Model):
    customer = models.CharField(max_length=100)
    created = models.DateTimeField()

    class Meta:
        index_together = [["customer", "created"]]


def recent_orders(request):
    now = datetime.datetime.now(tz=utc)
    orders = Order.objects.filter(created__lte=now)
    return JsonResponse({"count": orders.count()})
