from django.utils.crypto import constant_time_compare, get_random_string

TOKEN = get_random_string(12)
SAME = constant_time_compare("a", "a")
