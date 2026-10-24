from django.urls import path, re_path


def index(request):
    return None


urlpatterns = [
    path("", index, name="index"),
    re_path(r"^about/$", index, name="about"),
]
