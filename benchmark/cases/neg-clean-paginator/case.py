from django.core.paginator import Paginator

pages = Paginator(list(range(100)), 10)
FIRST = pages.page(1).object_list
