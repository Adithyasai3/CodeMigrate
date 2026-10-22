from django.contrib.auth.views import LogoutView
from django.http import JsonResponse
from django.utils.timezone import utc


class ShopLogoutView(LogoutView):
    def get_next_page(self):
        return "/"


def ping(request):
    return JsonResponse({"tz": str(utc)})
