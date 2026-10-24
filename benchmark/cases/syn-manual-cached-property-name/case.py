from django.utils.functional import cached_property


class Box:
    def _area(self):
        return 4

    area = cached_property(_area, name="area")


BOX = Box()
