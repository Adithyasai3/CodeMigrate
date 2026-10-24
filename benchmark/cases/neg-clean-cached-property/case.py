from django.utils.functional import cached_property


class Box:
    @cached_property
    def area(self):
        return 4


BOX = Box()
