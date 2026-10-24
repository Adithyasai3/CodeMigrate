from django.http import HttpResponse, JsonResponse

RESP = JsonResponse({"ok": True})
TEXT = HttpResponse("hi", content_type="text/plain")
