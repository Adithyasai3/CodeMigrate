from django.urls import register_converter


class FourDigitYear:
    regex = "[0-9]{4}"

    def to_python(self, value):
        return int(value)

    def to_url(self, value):
        return "%04d" % value


register_converter(FourDigitYear, "yyyy")
register_converter(FourDigitYear, "int")
