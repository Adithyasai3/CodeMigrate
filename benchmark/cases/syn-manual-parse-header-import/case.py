from django.http.multipartparser import parse_header

content_type, params = parse_header(b"text/plain; charset=utf-8")
