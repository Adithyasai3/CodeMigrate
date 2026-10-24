from django.utils.encoding import force_bytes, force_str, smart_str

A = force_str(b"abc")
B = force_bytes("abc")
C = smart_str(1)
