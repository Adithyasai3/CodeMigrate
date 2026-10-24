from django.utils.html import escape, format_html, strip_tags

SAFE = format_html("<b>{}</b>", "<script>")
TEXT = strip_tags("<p>hi</p>")
ESC = escape("<a>")
