from django.utils.html import format_html

banner = format_html("<b>Static banner</b>")
greeting = format_html("<i>{}</i>", "hi")
