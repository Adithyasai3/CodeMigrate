from django.contrib.sessions.serializers import PickleSerializer
from django.urls import register_converter
from django.http.multipartparser import parse_header


from django.db.models import Q

ACTIVE = Q(is_active=True)


payload = PickleSerializer().dumps({"cart": [1, 2]})



class FourDigitYear:
    regex = "[0-9]{4}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return "%04d" % value


register_converter(FourDigitYear, "yyyy")
register_converter(FourDigitYear, "int")


content_type, params = parse_header(b"text/plain; charset=utf-8")
